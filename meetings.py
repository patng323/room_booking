import random
import argparse
import pandas as pd
from util import Util
from meeting import Meeting


class Meetings:
    # TODO:
    # Extra properties:
    # - location (Truth building)

    def __init__(self, site):
        self._meetings = []
        self.num_meetings = 0
        self._site = site
        self.use_min_size = False

    @property
    def max_room_size(self):
        return self._site.max_room_size

    @property
    def max_timeslot(self):
        return self._site.max_timeslot

    def load_meeting_requests(self, paths, ratio=1.0):
        for path in paths:
            if path:
                df = Util.load_data(path, ratio)
                print(f"Records read: {len(df)}")
                for request in df.itertuples():
                    name = request.name
                    start, end = Util.parse_time_field(request.time)

                    if 'fixed' in df.columns:
                        fixed = request.fixed == 1
                    else:
                        fixed = False

                    if 'size' in df.columns:
                        size, min_size = Util.parse_size(request.size)
                    else:
                        size = min_size = 0  # No size is specified for this meeting; it's for fixed booking

                    # Note: the room field may contains multiple rooms.  E.g. 'G11, G12, G13'
                    # For the sake of room allocation, each room will be treated as a separate booking
                    rooms = [None]
                    if request.room and type(request.room) == str:
                        rooms = request.room.replace(', ', ',').split(',')

                    for room, i in zip(rooms, range(len(rooms))):
                        meeting = Meeting(name=name, meetings=self,
                                          size=size, min_size=min_size,
                                          fixed=fixed,
                                          room=room,
                                          start_time=start, end_time=end)
                        meeting.id = len(self._meetings)
                        self._meetings.append(meeting)

    def add_meeting(self, meeting):
        self._meetings.append(meeting)

    def detect_related_meetings(self):
        all_meetings = sorted(self._meetings, key=lambda m: m.name)

    def __iter__(self):
        for meeting in self._meetings:
            if meeting.suppressed:
                continue

            yield meeting

    def __getitem__(self, key):
        if type(key) == int:
            return self._meetings[key]
        else:
            res = []
            for m in self._meetings:
                if m.name == key:
                    res.append(m)

            if len(res) == 1:
                return res[0]
            else:
                return res

    def parse_excel_input(self, request):
        time_field = request["Time"]
        time_field = time_field.replace(" ", "")
        # TODO: finish it.....

    def import_requests(self, path, append=True):
        df = pd.read_excel(path)
        # TODO: finish it.....

    def genRandomInput(self, num_meetings):
        self.num_meetings = num_meetings
        self._meetings = []

        for i in range(num_meetings):
            meeting = Meeting(name=i, meetings=self)

            meeting.size = random.randint(2, self.max_room_size)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--topicIn", help="topic of input", default='dataInput')
    parser.add_argument("--countByClass", action="store_true")  # Boolean type
    parser.add_argument("--size", choices=[1, 2, 3], type=int, default=100)
    args = parser.parse_args()

    pass


if __name__ == "__main__":
    main()
