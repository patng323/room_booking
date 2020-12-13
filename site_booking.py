from collections import defaultdict
from rooms import Rooms
from meetings import Meetings, Meeting
from ortools.sat.python import cp_model
from datetime import datetime, date
from util import Util, MeetingRequestError
import pandas as pd
import numpy as np


def getid(meeting, timeslot, room):
    return f"{meeting.name}({meeting.id})", timeslot, room.name


class Site:
    CHECK_FAILED_MEETING_SIZE = -1
    CHECK_FAILED_NO_OF_MEETINGS = -2
    CHECK_FIXED_ROOM_CONFLICT = -3

    def __init__(self, rmbs, area: int, num_timeslots=None):
        self.rmbs = rmbs
        self.area = area

        if num_timeslots is None:
            # let's assume 8am to 10pm right now
            # Each timeslot is 30 mins
            num_timeslots = (22 - 8 + 1) * 2

        self.num_timeslots = num_timeslots
        self.timeslots = list(range(num_timeslots))

        self.rooms = None
        self.meetings = None
        self.__timeslot_requests = None
        self._solver = cp_model.CpSolver()
        self._solver.parameters.linearization_level = 0
        self._lastBookings = None
        self._lastStatus = None

    def load_site_info(self):
        self.rooms = Rooms()
        self.rooms.load_site_info(self.rmbs, self.area)

    def load_existing_meetings(self, meeting_date: date, ratio=1.0):
        assert self.rooms is not None
        self.meetings = Meetings(site=self)
        self.meetings.load_meeting_requests(self.rmbs, self.area, meeting_date, ratio)
        for m in self.meetings:
            assert m.room is None or m.room in self.rooms.room_names, f"Room '{m.room}' is not found"

        self.detect_related_meetings()

    def load_new_requests(self, path):
        df = pd.read_csv(path)
        print(f"Records read: {len(df)}")
        for request in df.itertuples():
            name = request.name
            start, end = Util.parse_time_field(request.time)
            size, min_size = Util.parse_size(request.size)
            self.addMeeting(name, size, start_time=start, end_time=end)

    def detect_related_meetings(self):
        all_meetings = sorted(self.meetings._meetings, key=lambda m: m.name)

    def genRandomInput(self, num_rooms, num_meetings):
        self.rooms = Rooms()
        self.rooms.genRandomInput(num_rooms)

        self.meetings = Meetings(site=self)
        self.meetings.genRandomInput(num_meetings)

    def addMeeting(self, name, size, start_timeslot=None, start_time=None, end_time=None, duration=None, needs_piano=False):
        meeting = Meeting(name=name, size=size, meetings=self.meetings, needs_piano=needs_piano,
                          start_timeslot=start_timeslot, start_time=start_time, end_time=end_time, duration=duration)
        self.meetings.add_meeting(meeting)
        self.__timeslot_requests = None

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
                piano = ''
                if meeting.needs_piano:
                    piano = '(P)'

                name = meeting.name
                if meeting.unit:
                    name += f" <{meeting.unit}>"
                if meeting.room:
                    name += f" : {meeting.room}"
                print(f"Meeting {name}: size={meeting.size}{piano}, timeslots={str(meeting.meeting_times)}")

        if print_rooms:
            print("---------------\n")
            for room in self.rooms:
                piano = ''
                if room.has_piano:
                    piano = '(P)'
                print("Room {rn}: cap={cap} {piano}".format(rn=room.name, cap=room.room_cap, piano=piano))

        if print_timeslots:
            print("---------------\n")
            for t in self.timeslots:
                ms = []
                for m in self.timeslot_requests[t]:
                    name = m.name
                    if m.room:
                        name += f" : {m.room}"

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
                    if meeting.room:
                        if meeting.room in room_booked_by:
                            msg = f"Timeslot {t} ({Util.timeslot_to_dt(t).strftime('%H:%M:%S')}): " + \
                                  f"Room '{meeting.room}' is requested by both:\n" + \
                                  f"'{room_booked_by[meeting.room]}'\n" + \
                                  f"'{meeting.name}'"
                            raise MeetingRequestError(msg,
                                                      {"code": self.CHECK_FIXED_ROOM_CONFLICT,
                                                       "timeslot": t,
                                                       "room": meeting.room,
                                                       "meeting1": room_booked_by[meeting.room],
                                                       "meeting2": meeting.name})
                        else:
                            room_booked_by[meeting.room] = meeting.name

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
            return 0

        return int((room.room_cap / meeting.size) * 10)

    @staticmethod
    def getBooking(bookings, model, meeting, time, room):
        id = getid(meeting, time, room)
        if id not in bookings:
            bookings[id] = model.NewBoolVar('{}'.format(id))

        return bookings[id]

    def createBookingModel(self, solution=None, ignore_piano=False, no_min_waste=False):
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
                    if m.room and len(m.room.strip()) > 0:
                        # The meeting already has a room specified
                        room_found = False
                        for r in self.rooms:
                            if m.room == r.name:
                                model.Add(self.getBooking(bookings, model, m, t, self.rooms.get_room(m.room)) == 1)
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

        # A room cannot hold more than one meeting
        for t in self.timeslots:
            for r in self.rooms:
                bookings_temp = []
                for m in self.meetings:
                    if self.checkRoomFit(r, m) and t in m.meeting_times:
                        bookings_temp.append(self.getBooking(bookings, model, m, t, r))

                if len(bookings_temp) > 0:
                    # Each room can be assigned only to one meeting
                    model.Add(sum(bookings_temp) <= 1)

        # A meeting must use the same room in all its required timeslots
        # (e.g. if meeting 1 span two timeslots, then ...)
        for m in self.meetings:
            for r in self.rooms:
                if self.checkRoomFit(r, m):
                    for i in range(len(m.meeting_times) - 1):
                        # For room r, if the current timeslot is TRUE, then the next one must be true too
                        model.Add(self.getBooking(bookings, model, m, m.meeting_times[i + 1], r) == True).OnlyEnforceIf(
                            self.getBooking(bookings, model, m, m.meeting_times[i], r))

        if not ignore_piano:
            # A room which requires piano must use a room that has a piano
            for m in self.meetings:
                for t in m.meeting_times:
                    for r in self.rooms:
                        if m.needs_piano and not r.has_piano:
                            model.Add(bookings[getid(m, t, r)] == 0)  # if the room as no piano, don't assign

        # Experiment 細房合併
        # Two groups of rooms cannot be booked at the same time
        # for combined_info in self.rooms.rooms_combined:
        #     small_rooms = combined_info['small_rooms']
        #     large_room = combined_info['large_room']
        #
        #     for t in self.timeslots:
        #         for small_room in small_rooms:
        #             bookings_temp = []
        #             for m in self.meetings:
        #                 if t in m.meeting_times:
        #                     bookings_temp.append(bookings[getid(m, t, large_room)])
        #                     bookings_temp.append(bookings[getid(m, t, small_room)])
        #
        #             # 若大房已 book, 細房不能 book, or vice versa
        #             model.Add(sum(bookings_temp) <= 1)
        #
        #     # TODO: we assume 拆細房 should be avoided?
        #     model.Minimize(sum(bookings[getid(m, t, r)]
        #                        for m in self.meetings for t in self.timeslots for r in small_rooms))

        if not no_min_waste:
            print("Minimize room space waste")
            model.Minimize(sum(self.bookingWaste(r, m) * bookings[getid(m, t, r)]
                               for m in self.meetings
                               for t in self.timeslots
                               for r in self.rooms
                               if getid(m, t, r) in bookings and m.room is None and not m.fixed))

        print(f"createBookingModel: end - {datetime.now()}")

        return model, bookings

    def meetings_which_need_piano(self):
        res = []
        for m in self.meetings:
            if m.needs_piano:
                res.append(m)

        return res

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
                        room = f'{r.name} ({r.room_cap})'
                        if room not in df:
                            df[room] = ""

                        waste = r.room_cap - m.size
                        s = f'{m.name} ({m.size}) (-{waste})'
                        if m.fixed or m.room:
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
                        if m.piano_suppressed:
                            name += "(PX)"
                            final_info = " piano suppressed"
                        elif m.needs_piano:
                            name += "(P)"
                            if not r.has_piano:
                                final_info = " !! piano not fulfilled"

                        if r.has_piano:
                            extra_rm = 'P'

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

    def resolve(self, ignore_piano=False, past_solution=None, max_time=180, no_min_waste=False):
        model, bookings = self.createBookingModel(solution=past_solution, ignore_piano=ignore_piano,
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

