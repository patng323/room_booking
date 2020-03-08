from __future__ import print_function
import random


class Meeting:
    MAX_SIZE = 100  # TODO: temp
    
    def __init__(self, name):
        self.__size = 0
        self.needs_piano = False
        self.__start_time = 0
        self.__duration = 0
        self.__end_time = 0
        self.__meeting_times = None
        self.name = name

    @property
    def size(self):
        return self.__size

    @size.setter
    def size(self, val):
        if val > self.MAX_SIZE:
            raise Exception("Meeting size is larger than max {}".format(self.MAX_SIZE))

        self.__size = val

    def set_time(self, start_time, duration, max_timeslot, truncate=False):
        self.__start_time = start_time
        if start_time + duration - 1 > max_timeslot:
            if truncate:
                duration = max_timeslot - start_time + 1
            else:
                raise Exception("start_time + duration has passed the max_timeslot allowed")

        self.__duration = duration
        self.__meeting_times = None

    @property
    def meeting_times(self):
        if self.__meeting_times is None:
            self.__meeting_times = list(range(self.__start_time, self.__start_time + self.__duration))

        return self.__meeting_times


class Meetings:
    # TODO:
    # Extra properties:
    # - location (Truth building)

    def __init__(self, max_meeting_size):
        self.meetings = []
        self.num_meetings = 0
        self.max_meeting_size = max_meeting_size

    def genRandomInput(self, num_meetings, num_timeslots):
        self.num_meetings = num_meetings
        self.meetings = []

        for i in range(num_meetings):
            meeting = Meeting(name=i)

            meeting.size = random.randint(2, self.max_meeting_size)
            start_time = random.randint(0, num_timeslots-1)

            if random.randint(1, 100) >= 80:
                meeting.needs_piano = True

            rn = random.randint(1, 100)
            if rn <= 50:
                duration = 1
            elif rn <= 90:
                duration = 2
            else:
                duration = 3

            meeting.set_time(start_time, duration, num_timeslots-1, truncate=True)
            self.meetings.append(meeting)

    def __iter__(self):
        for meeting in self.meetings:
            yield meeting
