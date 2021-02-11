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
        self.combined_rooms = []

    def load_site_info(self, rmbs: Rmbs, area: int):

        # Load room info from database
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

        # Also add combined room info
        rooms_combined_info = Util.load_rooms_combined_info(area)
        for info in rooms_combined_info:
            combined_room_cap = 0
            small_rooms = []
            for room in info['rooms']:
                small_rooms.append(self._rooms_dict[room])
                combined_room_cap += self._rooms_dict[room].room_cap

            combined_room = Room(room_cap=combined_room_cap, name="+".join(info['rooms']))
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

