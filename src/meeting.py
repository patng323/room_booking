from util import Util
import re

re_unit_match = re.compile(r"[^\(\)（）團班組]+(?:團契|團|班|小組|課程|門訓|廣場|fellowship|崇拜)", flags=re.IGNORECASE)
re_unit_match_eng = re.compile(r"([^\-]+)(?:\s{0,1}\-\s{0,1}.*|$)", flags=re.IGNORECASE)
re_english_name = re.compile(r'^[A-Za-z0-9\.\(\)\- ]+$')
special_units = ['男人天空']


def get_unit_from_name(name):
    for su in special_units:
        if su in name:
            return su

    # Handle English only case
    if re_english_name.match(name) is not None:
        srch = re_unit_match_eng.search(name)
        if srch and srch.groups():
            return srch.groups()[0].strip()

    res = re_unit_match.match(name)
    if res is not None:
        return res[0]

    return None


class Meeting:
    MAX_SIZE = 300  # TODO: temp

    def __init__(self, name, meetings,
                 description='',
                 room_name=None,
                 room_id=None,
                 size=0, min_size=0,
                 fixed=False,
                 facilities=None,
                 mrbs_entry_id=None,
                 start_timeslot=None, duration=None,
                 start_time=None, end_time=None):
        self.name = name
        self.unit = get_unit_from_name(name)  # 單位; e.g. 傷健科 : 尊主團

        self.__meetings = meetings  # Parent object

        self.description = description

        self.room_name = room_name.strip() if room_name else None  # Pre-assigned room
        self.room_id = room_id
        self.mrbs_entry_id = mrbs_entry_id

        self.__size = size
        # if the requested size is 8-10 ppl, then size=10, and minSize=8
        assert min_size == 0 or min_size <= size
        self.__min_size = min_size if min_size != 0 else size

        self.fixed = fixed

        self.facilities = facilities

        self.__start_timeslot = 0
        self.__duration = 0
        self.__meeting_times = None
        self.id = None  # id in mrbs_entry in DB

        if start_timeslot is not None:
            assert duration > 0 and start_time is None and end_time is None
            self.set_time(start_timeslot, duration)

        elif start_time is not None:
            assert end_time is not None and start_timeslot is None and duration is None
            start_timeslot = Util.dt_to_timeslot(start_time)

            end_timeslot = Util.dt_to_timeslot(end_time)

            # Note: if I book from 10:00 to 11:00, it means I want to book timeslots 10:00 and 10:30
            # That explains why we don't need to "add one" to the duration parameter below
            self.set_time(start_timeslot,
                          duration=end_timeslot - start_timeslot)

    @property
    def size(self):
        if self.__meetings.use_min_size:
            return self.__min_size
        else:
            return self.__size

    @size.setter
    def size(self, val):
        if val > self.MAX_SIZE:
            raise Exception("Meeting size is larger than max {}".format(self.MAX_SIZE))

        self.__size = val

    def set_time(self, start_time, duration, truncate=False):
        self.__start_timeslot = start_time
        if start_time + duration - 1 > self.__meetings.max_timeslot:
            if truncate:
                duration = self.__meetings.max_timeslot - start_time + 1  # Truncate the meeting duration
            else:
                raise Exception("start_time + duration has passed the max_timeslot allowed")

        self.__duration = duration
        self.__meeting_times = None

    @property
    def meeting_times(self):
        if self.__meeting_times is None:
            self.__meeting_times = list(range(self.__start_timeslot, self.__start_timeslot + self.__duration))

        return self.__meeting_times
