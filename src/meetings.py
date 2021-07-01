import random
import argparse
import pandas as pd
from util import Util
from meeting import Meeting
from rmbs import Rmbs
from datetime import date, datetime


class Meetings:
    # Represents all the meetings to be held in a site
    #
    #

    def __init__(self, site):
        self._meetings = []
        self.num_meetings = 0
        self._site = site  # The site in which the meetings are held
        self.use_min_size = False  # TODO: do we still need this var??

    @property
    def max_room_size(self):
        return self._site.max_room_size

    @property
    def max_timeslot(self):
        return self._site.max_timeslot

    def load_meeting_requests(self, rmbs: Rmbs, area: int, meeting_date: date, ratio=1.0):
        df = rmbs.read_meetings(area, meeting_date)
        if ratio < 1.0:
            df = df.head(n=int(len(df) * ratio))  # Use just a portion of the loaded meetings; mainly for test purpose

        print(f"Records read: {len(df)}")
        for request in df.itertuples():
            name = request.name
            start = datetime.fromtimestamp(request.start_time)
            end = datetime.fromtimestamp(request.end_time)

            fixed = True  # fixed == True means the meeting can't be moved anymore

            size = min_size = 0  # No size will be specified for this meeting, and it's a fixed booking

            # Note: for meeting which has already been assigned to a room, we don't care about its required facilities
            meeting = Meeting(name=name, meetings=self,
                              size=size, min_size=min_size,
                              fixed=fixed,
                              room_name=request.room_name,
                              room_id=request.room_id,
                              start_time=start, end_time=end,
                              mrbs_entry_id=request.id)

            meeting.id = request.id  # ID is the meeting ID in DB
            self._meetings.append(meeting)

    def add_meeting(self, meeting):
        self._meetings.append(meeting)

    def detect_related_meetings(self):
        all_meetings = sorted(self._meetings, key=lambda m: m.name)

    def __iter__(self):
        for meeting in self._meetings:
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
