# -*- coding: utf-8 -*-
import string
import random
from util import Util

feature_ids = {
    "投影機": 1,
    "鋼琴": 2,
    "副堂": 3,
}

class Room:
    MAX_SIZE = 300  # TODO: temp

    def __init__(self, room_cap=0, has_piano=False, name=None):
        self.room_cap = room_cap
        self.has_piano = False  # TODO: replaced by an array
        self.name = name


class Rooms:
    # TODO:
    # Extra properties:
    # - location (Truth building)
    def __init__(self):
        self.max_cap = 0
        self._rooms_dict = dict()

    def load_site_info(self, filepath):
        df = Util.load_data(filepath)
        self.max_cap = 0
        for info in df.itertuples():
            assert info.room not in self._rooms_dict, "same room shouldn't appear twice in input file"
            room = Room(room_cap=info.size, name=info.room)
            if info.size > self.max_cap:
                self.max_cap = info.size

            self._rooms_dict[info.room] = room

    @property
    def num_rooms(self):
        return len(self._rooms_dict)

    @property
    def rooms(self):
        return self._rooms_dict.values()

    @property
    def room_names(self):
        return self._rooms_dict.keys()

    def get_room(self, name):
        return self._rooms_dict[name]

    def genRandomInput(self, num_rooms=20):
        for rm in range(num_rooms):
            room = Room()
            room.name = string.ascii_letters[rm]
            room.room_cap = random.randint(8, 12)

            self.max_cap = max(room.room_cap, self.max_cap)
            self._rooms_dict[room.name] = room

        for room in self.rooms:
            if room.room_cap >= (self.max_cap - 3):
                room.has_piano = True

    def __iter__(self):
        for room in self.rooms:
            yield room

