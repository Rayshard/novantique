from dataclasses import dataclass
from threading import local
from typing import Any, Dict, List
import dotenv
import logging
from pprint import pprint
from pathlib import Path
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


config = dotenv.dotenv_values(Path(".") / ".env")

SLACK_API_TOKEN : str = config["SLACK_API_TOKEN"]
SLACK_BOT_CHANNEL : str = config["SLACK_BOT_CHANNEL"]
RECEIVERS : List[str] = [value for key, value in config.items() if key.startswith("RECEIVER")]


@dataclass
class GlobalEntryLocation:
    name: str
    id: int


def get_global_entry_locations() -> Dict[str, GlobalEntryLocation]:
    try:
        locations = requests.get("https://ttp.cbp.dhs.gov/schedulerapi/locations/?temporary=false&inviteOnly=false&operational=true&serviceName=Global%20Entry").json()
        result : Dict[str, GlobalEntryLocation] = dict()

        for location in locations:
            gel = GlobalEntryLocation(location["name"], location["id"])
            result[gel.name] = gel

        return result
    except Exception as e:
        logging.error(f"Unable to get global entry locations: {e}")
        return {}


def get_next_available_appt(location_id: int) -> str:
    return f"https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId={location_id}&minimum=1"


def send_message(client: WebClient, receiver: str, message: str) -> None:
    try:
        response = client.chat_postMessage(channel=receiver, text=message)
        assert response["message"]["text"] == message
    except SlackApiError as e:
        print(f"Unable to send message: {e.response['error']}")


def start() -> None:
    client = WebClient(token=SLACK_API_TOKEN)
    
    for receiver in RECEIVERS:
        send_message(client, receiver, "Hello from slack bot!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    start()