from django.db import models
import string
import random


ROOM_CODE_SYMBOLS = string.ascii_uppercase + string.digits


def generate_unique_room_code(length: int) -> str:
    '''Generates a random code of the specified length that is unique among the Room model.'''

    while True:
        code = ''.join(random.choices(ROOM_CODE_SYMBOLS, k=length))

        if Room.objects.filter(code=code).count() == 0:
            return code


class Room(models.Model):
    code = models.CharField(max_length=8, default="", unique=True)
    host = models.CharField(max_length=50, unique=True)
    guest_can_pause = models.BooleanField(null=False, default=False)
    votes_to_skip = models.IntegerField(null=False, default=1)
    created_at = models.DateTimeField(auto_now_add=True)