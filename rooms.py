# -*- coding: utf-8 -*-
from util import Util
from rmbs import Rmbs


class Room:
    MAX_SIZE = 300  # TODO: temp

    def __init__(self, room_cap=0, name=None, facilities=[]):
        self.room_cap = room_cap
        self.name = name
        self.facilities = facilities


class Rooms:
    def __init__(self):
        self.max_cap = 0
        self._rooms_dict = dict()
        self.rooms_combined = []

    def load_site_info(self, rmbs: Rmbs, area: int):
        df_building_info = rmbs.read_rooms(area)
        df_room_fac = rmbs.read_facility(area)
        self.max_cap = 0
        for info in df_building_info.itertuples():
            assert info.room_name not in self._rooms_dict, "same room shouldn't appear twice in input file"

            facilities = df_room_fac.query(f'room_id == {info.id}')['facility'].to_list()
            room = Room(room_cap=info.capacity, name=info.room_name, facilities=facilities)
            if info.capacity > self.max_cap:
                self.max_cap = info.capacity

            self._rooms_dict[info.room_name] = room

        rooms_combined_info = Util.load_rooms_combined_info(f"data/rooms_combined_info_{area}.csv")
        for combined in rooms_combined_info:
            large_room_cap = 0
            small_rooms = []
            for room in combined:
                small_rooms.append(self._rooms_dict[room])
                large_room_cap += self._rooms_dict[room].room_cap

            large_room = Room(room_cap=large_room_cap, name="+".join(combined))
            self._rooms_dict[large_room.name] = large_room
            self.rooms_combined.append({'large_room': large_room, 'small_rooms': small_rooms})

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

    def __iter__(self):
        for room in self.rooms:
            yield room

