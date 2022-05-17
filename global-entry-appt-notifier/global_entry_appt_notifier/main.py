from dataclasses import dataclass
import json
import traceback
from typing import Callable, Dict, List
import dotenv
import logging
import time
import jsonschema
from pathlib import Path
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import date, datetime


try:
    import pync
except:
    pass


def send_slack_message(client: WebClient, recipient: str, message: str) -> bool:
    try:
        client.chat_postMessage(channel=recipient, text=message)
    except SlackApiError as e:
        logging.error(f"Unable to send slack message: {e.response['error']}")
        return False

    return True

@dataclass
class Location:
    name: str
    id: int


@dataclass
class Appointment:
    location: Location
    start_time: datetime
    end_time: datetime


@dataclass
class Config:
    current_appt_date: date
    desired_locations: List[Location]
    notify_on_macos: bool
    notify_on_slack: bool


def get_all_locations() -> Dict[int, Location]:
    URL = "https://ttp.cbp.dhs.gov/schedulerapi/locations/?operational=true&serviceName=Global Entry"
    
    response = requests.get(URL).json()
    if not isinstance(response, list):
        logging.error("get_all_locations: request response is not a list")
        return {}

    result : Dict[int, Location] = {}

    for item in response:
        assert(isinstance(item, dict))

        loc_id = item.get("id")
        loc_name = item.get("name")

        result[loc_id] = Location(loc_name, loc_id)

    return result


def get_locations_with_appts_by(by_date: date) -> List[Location]:
    URL = f"https://ttp.cbp.dhs.gov/schedulerapi/slots/asLocations?minimum=1&filterTimestampBy=before&timestamp={by_date.isoformat()}&serviceName=Global%20Entry"

    response = requests.get(URL).json()
    if not isinstance(response, list):
        logging.error("get_locations_with_appts_by: request response is not a list")
        return []

    result : List[Location] = []

    for item in response:
        assert(isinstance(item, dict))

        loc_id = item.get("id")
        loc_name = item.get("name")

        result.append(Location(loc_name, loc_id))

    return result

def get_appts_by(loc: Location, by_date: date) -> List[Appointment]:
    URL = f"https://ttp.cbp.dhs.gov/schedulerapi/slots?filterTimestampBy=before&timestamp={by_date.isoformat()}&locationId={loc.id}&minimum=1"

    response = requests.get(URL).json()
    if not isinstance(response, list):
        logging.error("get_appts_by: request response is not a list")
        return []

    result : List[Appointment] = []

    for item in response:
        assert(isinstance(item, dict))

        start_time = datetime.fromisoformat(item.get("startTimestamp"))
        end_time = datetime.fromisoformat(item.get("endTimestamp"))

        result.append(Appointment(loc, start_time, end_time))

    return result


def load_config() -> Config:
    schema = {
        "type": "object",
        "properties": {
            "current_appt_date": {
                "type": "object",
                "properties": {
                    "year": { "type": "integer" },
                    "month": { "type": "integer" },
                    "day": { "type": "integer" },
                }
            },
            "locations": { "type": "array", "items": { "type": "integer" } },
            "notify_on_macos": { "type": "boolean" },
            "notify_on_slack": { "type": "boolean" },
        }
    }

    with open("config.json") as file:
        config = json.load(file)
        jsonschema.validate(config, schema)

        return Config(
            current_appt_date=date(config["current_appt_date"]["year"], config["current_appt_date"]["month"], config["current_appt_date"]["day"]),
            desired_locations=[loc for id, loc in get_all_locations().items() if id in config["locations"]],
            notify_on_macos=config["notify_on_macos"],
            notify_on_slack=config["notify_on_slack"]
        )

def run() -> None:
    # load config
    ENV = dotenv.dotenv_values(Path(".") / ".env")
    CONFIG = load_config()
    
    # set notifiers
    notifiers: List[Callable[[str], None]] = [lambda msg: logging.debug(msg)]

    if CONFIG.notify_on_slack:
        SLACK_API_TOKEN : str = ENV["SLACK_API_TOKEN"]
        RECIPIENTS : Dict[str, str] = {key.split('_', 1)[1].replace('_', ' '): value for key, value in ENV.items() if key.startswith("RECIPIENT")}

        client = WebClient(token=SLACK_API_TOKEN)

        for recipient_name, recipient_id in RECIPIENTS.items():
            send_slack_message(client, recipient_id, f"I have started checking for available appointments!")

        def slack_notifier(msg: str) -> None:
            for recipient_name, recipient_id in RECIPIENTS.items():
                logging.debug(f"Sending slack message to {recipient_name}...")

                if not send_slack_message(client, recipient_id, msg):
                    logging.debug(f"Failed to send slack message to {recipient_name}!")

        notifiers.append(slack_notifier)
    
    if CONFIG.notify_on_macos:
        pync.notify("Checking for appointment in the backgound!", title="Global Entry Appointment Notifier", sound="Pong")
        notifiers.append(lambda msg: pync.notify(msg, title="Global Entry Notifier", sound="Pong"))

    # query for appointments
    last_query : List[Appointment] = []

    while True:
        logging.debug("Querying for appointments...")
        query: List[Appointment] = []

        for loc in CONFIG.desired_locations:
            query += get_appts_by(loc, CONFIG.current_appt_date)

        new_appts = sorted([appt for appt in query if appt not in last_query], key=lambda appt: appt.start_time)

        if len(new_appts) != 0:
            logging.debug("New appointments found!")

            notifcation_msg = "Here are some newly available Global Entry appointments:"

            for i, appt in enumerate(new_appts):
                notifcation_msg += f"\n\n Appointment #{i}\n\tWHERE: {appt.location.name}\n\tTIME: {appt.start_time.ctime()}"

            notifcation_msg += "\n\n\n Visit https://ttp.cbp.dhs.gov/ to schedule a new appointment!"
            
            # send notifications
            logging.debug("Sending notifications...")

            for send_notification in notifiers:
                send_notification(notifcation_msg)
                time.sleep(1) # have a delay so that notifications don't overlap on the same device
        
            logging.debug("Done sending notifications.")
        else:
            logging.debug("No new appointments available.")

        last_query = query

        time.sleep(15)


if __name__ == "__main__":
    logging_file_handler = logging.FileHandler(f"output-{time.time_ns()}.log")
    logging_file_handler.setLevel(logging.ERROR)

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(), logging_file_handler]
    )

    num_restarts = 0
    restart_cooldown = 1 # number of seconds to wait before a restart

    while True:
        try:
            logging.info(f"Started." + (f"Restart #{num_restarts}" if num_restarts != 0 else ""))

            run()
        except Exception:
            logging.error(traceback.format_exc())
            logging.info(f"Restarting in {restart_cooldown} seconds...")

            time.sleep(restart_cooldown)

            restart_cooldown *= 2
            num_restarts += 1
