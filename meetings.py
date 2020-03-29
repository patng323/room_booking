from __future__ import print_function
import random
import argparse
import pandas as pd


class Meeting:
    MAX_SIZE = 100  # TODO: temp
    
    def __init__(self, name, meetings, size=0, needs_piano=False, start_time=None, duration=None, min_size=None):
        self.__size = size
        # if the requested size is 8-10 ppl, then size=10, and minSize=8
        assert min_size is None or min_size <= size
        self.__min_size = min_size if min_size is not None else size

        self.__needs_piano = needs_piano
        self.__piano_suppressed = False
        self.__meetings = meetings  # Parent object
        self.suppressed = False
        self.__start_time = 0
        self.__duration = 0
        self.__end_time = 0
        self.__meeting_times = None
        self.name = name

        if start_time is not None:
            assert duration > 0
            self.set_time(start_time, duration)

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
        self.__start_time = start_time
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
            self.__meeting_times = list(range(self.__start_time, self.__start_time + self.__duration))

        return self.__meeting_times


class Meetings:
    # TODO:
    # Extra properties:
    # - location (Truth building)

    def __init__(self, max_meeting_size, max_timeslot):
        self._meetings = []
        self.num_meetings = 0
        self.max_meeting_size = max_meeting_size
        self.max_timeslot = max_timeslot
        self.use_min_size = False

    def genRandomInput(self, num_meetings):
        self.num_meetings = num_meetings
        self._meetings = []

        for i in range(num_meetings):
            meeting = Meeting(name=i, meetings=self)

            meeting.size = random.randint(2, self.max_meeting_size)
            start_time = random.randint(0, self.max_timeslot)

            if random.randint(1, 100) >= 80:
                meeting.needs_piano = True

            rn = random.randint(1, 100)
            if rn <= 50:
                duration = 1
            elif rn <= 90:
                duration = 2
            else:
                duration = 3

            meeting.set_time(start_time, duration, truncate=True)
            self._meetings.append(meeting)

    def addMeeting(self, meeting):
        self._meetings.append(meeting)


    def __iter__(self):
        for meeting in self._meetings:
            if meeting.suppressed:
                continue

            yield meeting

    def __getitem__(self, key):
        return self._meetings[key]


    def parse_excel_input(self, request):
        time_field = request["Time"]
        time_field = time_field.replace(" ", "")

        # TODO: finish it.....


    def import_requests(self, path, append=True):
        df = pd.read_excel(path)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--topicIn", help="topic of input", default='dataInput')
    parser.add_argument("--countByClass", action="store_true")  # Boolean type
    parser.add_argument("--size", choices=[1, 2, 3], type=int, default=100)
    args = parser.parse_args()

    pass


if __name__ == "__main__":
    main()
