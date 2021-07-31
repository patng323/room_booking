from collections import defaultdict
from rooms import Rooms
from meetings import Meetings, Meeting
from ortools.sat.python import cp_model
from datetime import datetime, date
from util import Util, MeetingRequestError
import pandas as pd
from application import Application

def getid(meeting, timeslot, room):
    return f"{meeting.name}({meeting.meeting_times})({meeting.id})", timeslot, room.name


class Site:
    CHECK_FAILED_MEETING_SIZE = -1
    CHECK_FAILED_NO_OF_MEETINGS = -2
    CHECK_FIXED_ROOM_CONFLICT = -3

    def __init__(self, rmbs, area: int, num_timeslots=None):
        self.rmbs = rmbs
        self.area = area  # In RMBS, area represents a "building".  E.g. 教育樓

        if num_timeslots is None:
            # let's assume 8am to 10pm right now
            # Each timeslot is 30 mins
            num_timeslots = (22 - 8 + 1) * 2

        self.num_timeslots = num_timeslots
        self.timeslots = list(range(num_timeslots))

        self.rooms = None
        self.meetings = None
        self.requests = []
        self.__timeslot_requests = None
        self._solver = cp_model.CpSolver()
        self._solver.parameters.linearization_level = 0
        self._lastBookings = None  # the solutions from the last CP solver
        self._lastStatus = None
        self._dateLoaded = None

    def load_site_info(self):
        self.rooms = Rooms()  # Rooms represent all the rooms in a site
        self.rooms.load_site_info(self.rmbs, self.area)  # Load all the room info from DB

    def load_existing_meetings(self, meeting_date: date, ratio=1.0):
        assert self.rooms is not None, "Can't be called until all room info was loaded already"
        self.meetings = Meetings(site=self)
        self.meetings.load_meeting_requests(self.rmbs, self.area, meeting_date, ratio)  # Load meetings info from DB
        for m in self.meetings:
            assert m.room_name is None or m.room_name in self.rooms.room_names, f"Room '{m.room_name}' is not found"

        self.detect_related_meetings()
        self._dateLoaded = meeting_date

    def load_new_requests(self, path=None, df_requests=None):
        if path:
            df_requests = pd.read_csv(path)
            print(f"Records read: {len(df_requests)}")
        else:
            assert df_requests is not None

        fac_types = self.rmbs.read_facility_types().query(f'area_id == {self.area}')['type'].to_list()
        for request in df_requests.itertuples():

            if path:
                # This is for reading the input file used during development for testing
                name = request.name
                start, end = Util.parse_time_field(request.time)
                size, min_size = Util.parse_size(request.size)
                description = ''
                facilities = request.facilities
                if pd.isna(facilities):
                    facilities = None
                else:
                    facilities = facilities.split(",")
                    facilities = [x.strip() for x in facilities]
                    for fac in facilities:
                        assert fac in fac_types, f"{name} requested facility {fac} is not found in DB"
            else:
                name = Application.to_event_name(request._asdict())
                start = request.start_time
                end = request.stop_time
                size = min_size = request.size
                description = Application.to_description(request._asdict())
                # TODO: facilities aren't available in the form right now
                facilities = None

            if name.startswith("skip"):
                print(f'Request {name} is skipped')
                continue

            meeting = self.addMeeting(name, size, description=description, min_size=min_size, start_time=start, end_time=end,
                                      facilities=facilities)
            self.requests.append(meeting)

    def detect_related_meetings(self):
        all_meetings = sorted(self.meetings._meetings, key=lambda m: m.name)  # TODO: WIP.  E.g. Two 連貫 meetings: 馬其頓團契練歌，馬其頓團契

    def addMeeting(self, name, size, description='', min_size=0, start_timeslot=None, start_time=None, end_time=None,
                   duration=None, facilities=None):
        meeting = Meeting(name=name, description=description, size=size, min_size=min_size, meetings=self.meetings,
                          start_timeslot=start_timeslot, start_time=start_time, end_time=end_time, duration=duration,
                          facilities=facilities)
        self.meetings.add_meeting(meeting)
        self.__timeslot_requests = None

        return meeting

    @property
    def max_room_size(self):
        return self.rooms.max_cap

    @property
    def max_timeslot(self):
        return self.num_timeslots-1

    @property
    def timeslot_requests(self):
        if self.__timeslot_requests is None:
            self.__timeslot_requests = defaultdict(list)

            for meeting in self.meetings:
                for t in meeting.meeting_times:
                    self.__timeslot_requests[t].append(meeting)

        return self.__timeslot_requests

    def printConfig(self, print_meetings=True, print_rooms=True, print_timeslots=True):
        if print_meetings:
            print("---------------\n")
            for meeting in self.meetings:
                name = meeting.name
                if meeting.unit:
                    name += f" <{meeting.unit}>"
                if meeting.room_name:
                    name += f" : {meeting.room_name}"
                print(f"Meeting {name}: size={meeting.size}, timeslots={str(meeting.meeting_times)}")

        if print_rooms:
            print("---------------\n")
            for room in self.rooms:
                if room.facilities:
                    fac = f'[{",".join(room.facilities)}]'
                else:
                    fac = ''
                print(f"Room {room.name}: cap={room.room_cap} {fac}")

        if print_timeslots:
            print("---------------\n")
            for t in self.timeslots:
                ms = []
                for m in self.timeslot_requests[t]:
                    name = m.name
                    if m.room_name:
                        name += f" : {m.room_name}"

                    ms.append(name)

                print(f"Time {t}: {ms} ({len(ms)})")

        print("---------------\n")

    def basicCheck(self):
        room_caps_sorted = sorted([room.room_cap for room in self.rooms], reverse=True)

        for t in self.timeslots:
            tr = self.timeslot_requests[t]
            if len(tr) > 0:
                # Check if any 'fixed room' requests have conflict
                room_booked_by = {}
                for meeting in tr:
                    if meeting.room_name:
                        if meeting.room_name in room_booked_by:
                            existing_booking = room_booked_by[meeting.room_name]
                            msg = f"Timeslot {t} ({Util.timeslot_to_dt(t).strftime('%H:%M:%S')}): " + \
                                  f"Room '{meeting.room_name}' is requested by both:\n" + \
                                  f"'{existing_booking.name} ({existing_booking.mrbs_entry_id})'\n" + \
                                  f"'{meeting.name} ({meeting.mrbs_entry_id})'"
                            raise MeetingRequestError(msg,
                                                      {"code": self.CHECK_FIXED_ROOM_CONFLICT,
                                                       "timeslot": t,
                                                       "room": meeting.room_name,
                                                       "meeting1": existing_booking.name,
                                                       "meeting1_id": existing_booking.mrbs_entry_id,
                                                       "meeting2": meeting.name,
                                                       "meeting2_id": meeting.mrbs_entry_id})
                        else:
                            room_booked_by[meeting.room_name] = meeting

                if len(tr) > self.rooms.num_rooms:
                    msg = 'Too many meetings (total: {}) are booked at time {}'.format(len(tr), t)
                    raise MeetingRequestError(msg, {"code": self.CHECK_FAILED_NO_OF_MEETINGS, "timeslot": t})

                sizes_sorted = sorted([(m, m.size) for m in tr], key=lambda x: x[1],
                                      reverse=True)
                for i in range(len(sizes_sorted)):
                    if sizes_sorted[i][1] > room_caps_sorted[i]:
                        msg = 'Meeting {m} cannot find a fitting room (of size {s}) at time {t}\n'.format(
                            m=sizes_sorted[i][0].name, s=sizes_sorted[i][1], t=t) + \
                            'Caps of all rooms: \n{}'.format(room_caps_sorted) + \
                            'Sizes of meeting at time {t}: \n{s}'.format(t=t, s=str([x[1] for x in sizes_sorted]))
                        raise MeetingRequestError(msg, {"code": self.CHECK_FAILED_MEETING_SIZE, "timeslot": t})

    @staticmethod
    def checkRoomFit(room, meeting):
        # By avoiding assigning BIG rooms to SMALL meeting, we reduce the number of branches when calculating the soln.
        if room.room_cap < meeting.size:
            return False
        elif meeting.size <= 10:
            return room.room_cap <= 50
        elif meeting.size <= 30:
            return room.room_cap <= 100
        else:
            return True

    @staticmethod
    def bookingWaste(room, meeting):
        waste = room.room_cap - meeting.size

        if waste <= 5:
            # Help reduce number of branches
            return 0

        return int((room.room_cap / meeting.size) * 10)

    @staticmethod
    def getBooking(bookings, model, meeting, time, room):
        id = getid(meeting, time, room)
        if id not in bookings:
            bookings[id] = model.NewBoolVar('{}'.format(id))

        return bookings[id]

    def createBookingModel(self, solution=None, no_min_waste=False):
        print(f"createBookingModel: start - {datetime.now()}")

        model = cp_model.CpModel()
        bookings = {}

        # If we have a set of allocations we should follow, let's set condition for them first
        if solution:
            print("createBookingModel: we have a past solution to follow")
            for m in self.meetings:
                for r in self.rooms:
                    for t in self.timeslots:
                        if getid(m, t, r) in solution["alloc"]:
                            # This exact [meeting, timeslot, room] combination has been set in the past solution
                            model.Add(self.getBooking(bookings, model, m, t, r) == 1)

        # A meeting must happen at its specified time slots
        for m in self.meetings:
            for t in self.timeslots:
                if t in m.meeting_times:
                    if m.room_name:
                        # The meeting already has a room specified
                        room_found = False
                        for r in self.rooms:
                            if m.room_name == r.name:
                                model.Add(self.getBooking(bookings, model, m, t, self.rooms.get_room(m.room_name)) == 1)
                                room_found = True
                                break

                        assert room_found, f'The room specified in {str(m)} cannot be found'
                    else:
                        # if meeting m needs timeslot t, we need to book exactly one room at timeslot t
                        # for those rooms that fit the size
                        model.Add(
                            sum(self.getBooking(bookings, model, m, t, r)
                                for r in self.rooms
                                if self.checkRoomFit(r, m)) == 1)

        # A room cannot hold more than one meeting at the same time
        for t in self.timeslots:
            for r in self.rooms:
                bookings_temp = []
                for m in self.meetings:
                    if self.checkRoomFit(r, m) and t in m.meeting_times:
                        bookings_temp.append(self.getBooking(bookings, model, m, t, r))

                if len(bookings_temp) > 0:
                    # Each room can be assigned only to one meeting
                    model.Add(sum(bookings_temp) <= 1)

        # A meeting must use the same room in all its required timeslots.  That is, a meeting cannot 轉房.
        for m in self.meetings:
            for r in self.rooms:
                if self.checkRoomFit(r, m):
                    for i in range(len(m.meeting_times) - 1):
                        # For room r, if the current timeslot is TRUE, then the next one must be true too
                        model.Add(self.getBooking(bookings, model, m, m.meeting_times[i + 1], r) == True).OnlyEnforceIf(
                            self.getBooking(bookings, model, m, m.meeting_times[i], r))

        # Facility checking
        for m in self.meetings:
            if not m.room_name and m.facilities:  # The meeting isn't assigned a room yet, and it needs facility
                for t in m.meeting_times:
                    for r in self.rooms:
                        room_has_all_needed_fac = all([needed_fac in r.facilities for needed_fac in m.facilities])
                        if not room_has_all_needed_fac:
                            # if the room doesn't have all needed facility, don't allow it to hold the meeting
                            model.Add(self.getBooking(bookings, model, m, t, r) == 0)

        # All the things we want to minimize
        to_minimize = []

        # 細房 and the combined 大房 cannot be booked at the same time
        for combined_info in self.rooms.combined_rooms:
            small_rooms = combined_info['small_rooms']
            large_room = combined_info['combined_room']

            whole_day_bookings_for_small_rooms = []
            whole_day_bookings_for_large_room = []

            for t in self.timeslots:
                booking_large = self.getBooking(bookings, model, m, t, large_room)
                # Boost the cost factor, so that it has higher priority over "room waste" during minimize
                whole_day_bookings_for_large_room.append(50 * booking_large)

                for small_room in small_rooms:
                    # All the bookings for this small room and its corresponding large room at time t
                    bookings_temp = []
                    for m in self.meetings:
                        if t in m.meeting_times:
                            bookings_temp.append(booking_large)

                            booking_small = self.getBooking(bookings, model, m, t, small_room)
                            # Boost the cost factor, so that it has higher priority over "room waste" during minimize
                            whole_day_bookings_for_small_rooms.append(50 * booking_small)
                            bookings_temp.append(booking_small)

                    # At this timeslot, the 細房 and its corresponding 大房 can't be booked at the same time.
                    model.Add(sum(bookings_temp) <= 1)

            if combined_info['normal'] == 'combined':
                # Throughout the whole day, 拆細房 should be avoided
                to_minimize.extend(whole_day_bookings_for_small_rooms)
            else:
                assert combined_info['normal'] == 'split'
                # Throughout the whole day, 變大房 should be avoided
                to_minimize.extend(whole_day_bookings_for_large_room)

        # Minimize room space waste
        to_minimize.extend(self.bookingWaste(r, m) * bookings[getid(m, t, r)]
                           for m in self.meetings
                           for t in self.timeslots
                           for r in self.rooms
                           if getid(m, t, r) in bookings and m.room_name is None and not m.fixed)

        # Now call model.Minimize to minimize everything
        model.Minimize(sum(to_minimize))

        print(f"createBookingModel: end - {datetime.now()}")

        return model, bookings

    def save_one_solution(self):
        allocations = []
        for m in self.meetings:
            for r in self.rooms:
                for t in self.timeslots:
                    id = getid(m, t, r)
                    if id in self._lastBookings:
                        if self._solver.Value(self._lastBookings[id]):
                            allocations.append(getid(m, t, r))

        return {"alloc": allocations}

    def export_solution(self, solution, fn):
        df = pd.DataFrame(columns=["Time"])
        for t, i in zip(self.timeslots, range(len(self.timeslots))):
            df = df.append({'Time': Util.timeslot_to_str(t)}, ignore_index=True)
            for m in self.meetings:
                for r in self.rooms:
                    if getid(m, t, r) in solution["alloc"]:
                        room = f'{r.name} ({r.room_cap_original}/{r.room_cap})'
                        if r.facilities:
                            room += f' ({", ".join(r.facilities)})'
                        if room not in df:
                            df[room] = ""

                        waste = r.room_cap - m.size
                        s = f'{m.name} ({m.size}) (-{waste})'
                        if m.fixed or m.room_name:
                            s += " *"  # Fixed, or has room specified in the request already
                        elif waste > 10:
                            print(f"Big waste detected: {Util.timeslot_to_str(t)} - {s}")

                        df.at[i, room] = s

        room_cols = set(df.columns)
        room_cols.remove('Time')
        room_cols = list(room_cols)
        room_cols.sort()
        cols = ["Time"]
        cols.extend(room_cols)

        df[cols].to_csv(fn, index=False, na_rep='', encoding='utf_8_sig')

    def export_new_bookings(self, solution, filename=None, write_to_db=False):
        df = pd.DataFrame(columns=["Date", "Name", "Time", "Require", "Size", "Room", "Cap", "Cap_Real", "Facilities"])

        new_meetings_info = []
        for m in self.meetings:
            if m.fixed:
                continue

            for r in self.rooms:
                times = []
                for t in self.timeslots:
                    if getid(m, t, r) in solution["alloc"]:
                        times.append(t)

                if times:
                    assert times == m.meeting_times
                    df = df.append({"Date": self._dateLoaded.strftime("%Y-%m-%d"),
                                    "Name": m.name, "Size": m.size,
                                    "Time": Util.timeslot_to_str([times[0], times[-1]+1]),
                                    "Require": "" if not m.facilities else ", ".join(m.facilities),
                                    "Room": r.name,
                                    "Facilities": "" if not r.facilities else ", ".join(r.facilities),
                                    "Cap_Real": r.room_cap_original,
                                    "Cap": r.room_cap},
                                   ignore_index=True)

                    new_meetings_info.append({"meeting": m, "room": r})
                    break

        if filename:
            df.to_csv(filename, index=False, na_rep='', encoding='utf_8_sig')

        if write_to_db:
            new_entry_ids = self.rmbs.insert_meetings(new_meetings_info, self._dateLoaded)
        else:
            new_entry_ids = []

        return df, new_entry_ids

    @staticmethod
    def send_new_bookings_email(df_new_bookings: pd.DataFrame):
        df_new_bookings = df_new_bookings.fillna("").rename(
            {"Date": "日期",
             "Name": "名稱",
             "Time": "時間",
             "Require": "所需設備",
             "Size": "人數",
             "Room": "房間",
             "Cap": "容量（2/3）",
             "Cap_Real": "容量（全）",
             "Facilities": "設備"},
            axis='columns'
        )

        booking_table = df_new_bookings.to_html(index=False, justify='left', border=1)

        html = f"""\
<html>
  <head>
    <style> 
        body {{font-size:10p}}
        table, th, td {{font-size:10pt; border:1px solid black; border-collapse:collapse; text-align:left;}}
        th, td {{padding: 5px;}}
    </style>
  </head>
  房間預約自動分配結果
  <br/><br/>
  <body>
  {booking_table}
  </body>
</html>
"""

        Util.send_email("房間預約分配結果 - 成功", html)

    def send_no_solution_email(self):
        df = pd.DataFrame(columns=["Date", "Name", "Time", "Require"])

        for m in self.requests:
            df = df.append({"Date": self._dateLoaded.strftime("%Y-%m-%d"),
                            "Name": m.name, "Size": m.size,
                            "Time": Util.timeslot_to_str([m.meeting_times[0], m.meeting_times[-1]+1]),
                            "Require": "" if not m.facilities else ", ".join(m.facilities),
                            "Size": m.size},
                           ignore_index=True)

        df = df.fillna("").rename(
            {"Date": "日期",
             "Name": "名稱",
             "Time": "時間",
             "Require": "所需設備",
             "Size": "人數"},
            axis='columns'
        )

        booking_table = df.to_html(index=False, justify='left', border=1)

        html = f"""\
    <html>
      <head>
        <style> 
            body {{font-size:10p}}
            table, th, td {{font-size:10pt; border:1px solid black; border-collapse:collapse; text-align:left;}}
            th, td {{padding: 5px;}}
        </style>
      </head>
      房間預約自動分配結果: 未能成功分配
      <br/><br/>
      <body>
      {booking_table}
      </body>
    </html>
    """

        Util.send_email("房間預約分配結果 - 失敗", html)


    def print_one_solution(self, solution):
        booking_allocated = set()
        for t in self.timeslots:
            print(f'Time {t} ({Util.timeslot_to_str(t)})')
            for m in self.meetings:
                for r in self.rooms:
                    if getid(m, t, r) in solution["alloc"]:
                        booking_allocated.add(m.name)
                        extra_rm = mtg_times_info = final_info = ''
                        name = str(m.name)

                        if len(m.meeting_times) > 1:
                            if m.meeting_times[0] == t:
                                mtg_times_info = '*'
                            else:
                                mtg_times_info = '.'

                        if extra_rm:
                            extra_rm = '(' + extra_rm + ')'
                        print(
                            f'  Mtg-{name}{mtg_times_info} (size:{m.size}) assigned to {r.name}{extra_rm} '
                            f'(cap:{r.room_cap}) (waste={(r.room_cap - m.size)}) {final_info}'
                        )
        print()
        print("Meeting allocated total: {}".format(len(booking_allocated)))

    def resolve(self, past_solution=None, max_time=180, no_min_waste=False):
        model, bookings = self.createBookingModel(solution=past_solution,
                                                  no_min_waste=no_min_waste)
        self._lastBookings = bookings

        self._solver.parameters.max_time_in_seconds = max_time

        status = self._solver.Solve(model)
        status = self._solver.StatusName(status)
        self._lastStatus = status

        if status != 'INFEASIBLE':
            solution = self.save_one_solution()
        else:
            solution = None

        return status, solution

    def printStats(self):
        print("Solve returns: " + self._lastStatus)
        print()
        print('Statistics')
        print('  - conflicts       : %i' % self._solver.NumConflicts())
        print('  - branches        : %i' % self._solver.NumBranches())
        print('  - wall time       : %f s' % self._solver.WallTime())
        print()

    @staticmethod
    def send_too_late_bookings_email(df_apps: pd.DataFrame):
        df_apps = df_apps.fillna("").rename(
            {"register_time": "交表時間",
             "description": "申請詳情",
             "event_site": "地點",
             "event_date": "聚會日期",
             "start_time": "開始時間",
             "stop_time": "結束時間",
             "size": "人數",
             "application_file": "申請檔案"},
            axis='columns'
        )

        table = df_apps.to_html(index=False, justify='left', border=1)

        html = f"""\
<html>
  <head>
    <style> 
        body {{font-size:10p}}
        table, th, td {{font-size:10pt; border:1px solid black; border-collapse:collapse; text-align:left;}}
        th, td {{padding: 5px;}}
    </style>
  </head>
  過來日子限期的申請
  <br/><br/>
  <body>
  {table}
  </body>
</html>
"""
        Util.send_email("過來日子限期的申請", html)


