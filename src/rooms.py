# -*- coding: utf-8 -*-
from util import Util
from rmbs import Rmbs
import math


class Room:
    MAX_SIZE = 300  # TODO: temp

    def __init__(self, room_cap=0, name=None, id=None, facilities=[], small_rooms=[], room_cap_ratio=2/3):
        self.room_cap_original = room_cap
        self.name = name
        self.facilities = facilities
        self.room_cap_ratio = room_cap_ratio
        self.small_rooms = small_rooms
        self.id = id  # It can be a list of ids if it's a combined room

    @property
    def room_cap(self):
        return math.ceil(self.room_cap_original * self.room_cap_ratio)

    @property
    def is_combined(self):
        return len(self.small_rooms) > 0


class Rooms:
    def __init__(self):
        self.max_cap = 0
        self._rooms_dict = dict()
        self.combined_rooms = []

    def load_site_info(self, rmbs: Rmbs, area: int):

        # Load room info from database
        df_building_info = rmbs.read_rooms(area)
        df_room_fac = rmbs.read_facility(area)
        self.max_cap = 0
        for info in df_building_info.itertuples():
            assert info.room_name not in self._rooms_dict, f"same room ({info.room_name}) shouldn't appear from input"

            facilities = df_room_fac.query(f'room_id == {info.id}')['facility'].to_list()
            room = Room(room_cap=info.capacity, name=info.room_name, id=info.id, facilities=facilities)
            if info.capacity > self.max_cap:
                self.max_cap = info.capacity

            self._rooms_dict[info.room_name] = room

        # Also add combined room info
        rooms_combined_info = Util.load_rooms_combined_info(area)
        for info in rooms_combined_info:
            combined_room_cap = 0
            small_rooms = []
            facilities = []
            for room in info['rooms']:
                room_info = self._rooms_dict[room]
                small_rooms.append(room_info)
                combined_room_cap += room_info.room_cap
                facilities.extend(room_info.facilities)

            combined_room = Room(room_cap=combined_room_cap, name="+".join(info['rooms']),
                                 facilities=facilities, small_rooms=small_rooms, id=[r.id for r in small_rooms])
            self._rooms_dict[combined_room.name] = combined_room
            self.combined_rooms.append({'combined_room': combined_room, 'small_rooms': small_rooms,
                                        'normal': info['normal']})

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

