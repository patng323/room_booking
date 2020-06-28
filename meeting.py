from util import Util

class Meeting:
    MAX_SIZE = 300  # TODO: temp

    def __init__(self, name, meetings,
                 room=None,
                 size=0, min_size=0,
                 fixed=False,
                 needs_piano=False,
                 start_timeslot=None, duration=None,
                 start_time=None, end_time=None):
        self.name = name
        self.__meetings = meetings  # Parent object

        self.room = room  # Pre-assigned room

        self.__size = size
        # if the requested size is 8-10 ppl, then size=10, and minSize=8
        assert min_size == 0 or min_size <= size
        self.__min_size = min_size if min_size != 0 else size

        self.fixed = fixed

        self.__needs_piano = needs_piano
        self.__piano_suppressed = False
        self.suppressed = False

        self.__start_timeslot = 0
        self.__duration = 0
        self.__end_time = 0
        self.__meeting_times = None
        self.id = None

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

    def suppress_piano(self, suppress=True):
        self.__piano_suppressed = suppress

    @property
    def piano_suppressed(self):
        return self.__piano_suppressed

    @property
    def needs_piano(self):
        if self.__piano_suppressed:
            return False
        else:
            return self.__needs_piano

    @needs_piano.setter
    def needs_piano(self, val):
        self.__needs_piano = val

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
                duration = self.__meetings.max_timeslot - start_time + 1
            else:
                raise Exception("start_time + duration has passed the max_timeslot allowed")

        self.__duration = duration
        self.__meeting_times = None

    @property
    def meeting_times(self):
        if self.__meeting_times is None:
            self.__meeting_times = list(range(self.__start_timeslot, self.__start_timeslot + self.__duration))

        return self.__meeting_times
