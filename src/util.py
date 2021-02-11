# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta
import pandas as pd
from rmbs import Rmbs

_startTime = datetime(year=1900, month=1, day=1, hour=8, minute=0)


class Util:

    @staticmethod
    def parse_time_field(time_field: str):
        time_field = time_field.replace(" ", "")
        time_field = time_field.replace("：", ":")  # Replace the chinese colon by the standard one
        parts = time_field.split("-")
        assert len(parts) == 2

        parts_time = []

        for part in parts:
            pm = False
            part = part.lower()
            m = re.search("am|pm|上午|下午", part)
            if m:
                if m.group() in ["pm", "下午"]:
                    pm = True

                part = part.replace(m.group(), "")

            part_time = datetime.strptime(part, "%H:%M")
            if pm:
                assert part_time.hour <= 12
                if part_time.hour != 12:
                    # Note: 12pm is a special case, where we don't need to adjust the time
                    part_time += timedelta(hours=12)

            parts_time.append(part_time)

        return parts_time[0], parts_time[1]

    @staticmethod
    def dt_to_timeslot(value: datetime):
        return int(((value.hour * 60 + value.minute) -
                    (_startTime.hour * 60 + _startTime.minute)) / 30)

    @staticmethod
    def timeslot_to_dt(value: int):
        return _startTime + timedelta(minutes=value * 30)

    @staticmethod
    def timeslot_to_str(value: int):
        s = f"{datetime.strftime(Util.timeslot_to_dt(value), '%H:%M')} - " \
            f"{datetime.strftime(Util.timeslot_to_dt(value) + timedelta(minutes=30), '%H:%M')}"
        return s

    @staticmethod
    def parse_size(value: str):
        value = value.replace('人', '')
        value = value.replace(' ', '')
        parts = value.split('-')
        if len(parts) == 1:
            size = int(parts[0])
            min_size = 0
        else:
            min_size = int(parts[0])
            size = int(parts[1])

        return size, min_size

    @staticmethod
    def load_rooms_combined_info(area: int):
        df = pd.read_csv(f"data/rooms_combined_info_area_{area}.csv")
        rooms_combined_info = []
        for row in df.itertuples():
            info = {'normal': row.normal, 'rooms': []}
            for room in row.rooms.split(','):
                room = room.strip().replace(' ', '')
                info['rooms'].append(room)

            rooms_combined_info.append(info)

        return rooms_combined_info


class MeetingRequestError(Exception):
    def __init__(self, message, detail=None):
        self.message = message
        self.detail = detail
        super().__init__(self.message + "\nDetail:\n{}".format(self.detail))






