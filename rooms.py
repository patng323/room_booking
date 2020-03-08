from __future__ import print_function
import string
import random


class Room:
    MAX_SIZE = 100  # TODO: temp

    def __init__(self):
        self.room_cap = 0
        self.has_piano = False
        self.name = None


class Rooms:
    # TODO:
    # Extra properties:
    # - location (Truth building)
    def __init__(self):
        self.num_rooms = 0
        self.max_cap = 0
        self.rooms = []

    def genRandomInput(self, num_rooms=20):
        self.num_rooms = num_rooms

        for rm in range(num_rooms):
            room = Room()
            room.name = string.ascii_letters[rm]
            room.room_cap = random.randint(8, 12)

            self.rooms.append(room)
            self.max_cap = max(room.room_cap, self.max_cap)

        for room in self.rooms:
            if room.room_cap >= (self.max_cap - 3):
                room.has_piano = True

    def __iter__(self):
        for room in self.rooms:
            yield room

