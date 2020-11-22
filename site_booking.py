from collections import defaultdict
from rooms import Rooms
from meetings import Meetings, Meeting
from ortools.sat.python import cp_model
from datetime import datetime
from util import Util, MeetingRequestError
import pandas as pd
import numpy as np


def getid(meeting, timeslot, room):
    return f"{meeting.name}({meeting.id})", timeslot, room.name


class Site:
    CHECK_FAILED_MEETING_SIZE = -1
    CHECK_FAILED_NO_OF_MEETINGS = -2
    CHECK_FIXED_ROOM_CONFLICT = -3

    def __init__(self, name, num_timeslots=None):
        self.name = name

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
        self.rooms.load_site_info(f"data/building_info_{self.name}.csv")

    def load_meeting_requests(self, paths, ratio=1.0):
        assert self.rooms is not None
        self.meetings = Meetings(site=self)
        self.meetings.load_meeting_requests(paths, ratio)
        for m in self.meetings:
            assert m.room is None or m.room in self.rooms.room_names, f"Room '{m.room}' is not found"

        self.detect_related_meetings()

    def detect_related_meetings(self):
        all_meetings = sorted(self.meetings._meetings, key=lambda m: m.name)

    def genRandomInput(self, num_rooms, num_meetings):
        self.rooms = Rooms()
        self.rooms.genRandomInput(num_rooms)

        self.meetings = Meetings(site=self)
        self.meetings.genRandomInput(num_meetings)

    def addMeeting(self, name, size, start_time, duration, needs_piano=False):
        meeting = Meeting(name=name, size=size, meetings=self.meetings, needs_piano=needs_piano,
                          start_timeslot=start_time, duration=duration)
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

    def createBookingModel(self, solution=None, ignore_piano=False):
        print(f"createBookingModel: start - {datetime.now()}")

        model = cp_model.CpModel()
    
        bookings = {}
        for m in self.meetings:
            for t in self.timeslots:
                for r in self.rooms:
                    # bookings[id(m, t, r] = 1 if meeting m has booked room r at time t
                    bookings[getid(m, t, r)] = model.NewBoolVar('{}'.format(getid(m, t, r)))

        # If we have a set of allocations we should follow, let's set condition for them first
        # TODO: will they conflict with 'fixed' meetings?
        if solution:
            print("createBookingModel: we have a past solution to follow")
            for t in self.timeslots:
                for m in self.meetings:
                    for r in self.rooms:
                        if getid(m, t, r) in solution["alloc"]:
                            # This exact [meeting, timeslot, room] combination has been set in the past solution
                            model.Add(bookings[getid(m, t, r)] == 1)

        # A meeting must happen at its specified time slots
        for m in self.meetings:
            for t in self.timeslots:
                if t in m.meeting_times:
                    # Set conditions for "fixed" meetings
                    if m.fixed:
                        for r in self.rooms:
                            if m.room == r.name:
                                # A fixed room
                                model.Add(bookings[getid(m, t, self.rooms.get_room(m.room))] == 1)
                            else:
                                # Make sure we don't book other rooms
                                model.Add(bookings[getid(m, t, r)] == 0)
                    else:
                        # if meeting m needs timeslot t, we need to book exactly one room at timeslot t
                        model.Add(sum(bookings[getid(m, t, r)] for r in self.rooms) == 1)
                else:
                    # Meeting m doesn't need this timeslot.  So don't assign it to any room at timeslot t
                    for r in self.rooms:
                        model.Add(bookings[getid(m, t, r)] == 0)
    
        # No two meetings can share the same room
        for t in self.timeslots:
            for r in self.rooms:
                bookings_temp = []
                for m in self.meetings:
                    if t in m.meeting_times:
                        bookings_temp.append(bookings[getid(m, t, r)])

                if len(bookings_temp) > 0:
                    # Each room can be assigned only to one meeting
                    model.Add(sum(bookings_temp) <= 1)
    
        # The room capacity must fit the meeting size
        for m in self.meetings:
            for t in m.meeting_times:
                for r in self.rooms:
                    if r.room_cap < m.size:
                        model.Add(bookings[getid(m, t, r)] == 0)

        # A meeting must use the same room in all its required timeslots
        # (e.g. if meeting 1 span two timeslots, then ...)
        for m in self.meetings:
            for r in self.rooms:
                for i in range(len(m.meeting_times) - 1):
                    # For room r, if the current timeslot is TRUE, then the next one must be true too
                    model.Add(bookings[getid(m, m.meeting_times[i + 1], r)] == True).OnlyEnforceIf(
                        bookings[getid(m, m.meeting_times[i], r)])
    
        if not ignore_piano:
            # A room which requires piano must use a room that has a piano
            for m in self.meetings:
                for t in m.meeting_times:
                    for r in self.rooms:
                        if m.needs_piano and not r.has_piano:
                            model.Add(bookings[getid(m, t, r)] == 0)  # if the room as no piano, don't assign

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
        for t in self.timeslots:
            for m in self.meetings:
                for r in self.rooms:
                    if self._solver.Value(self._lastBookings[getid(m, t, r)]):
                        allocations.append(getid(m, t, r))

        return {"alloc": allocations}

    def export_solution(self, solution, fn):
        df = pd.DataFrame(columns=["Time"])
        for t, i in zip(self.timeslots, range(len(self.timeslots))):
            df = df.append({'Time': Util.timeslot_to_str(t)}, ignore_index=True)
            for m in self.meetings:
                for r in self.rooms:
                    if getid(m, t, r) in solution["alloc"]:
                        if r.name not in df:
                            df[r.name] = ""

                        df.at[i, r.name] = m.name

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
            print('Time %i' % t)
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

    def resolve(self, ignore_piano=False, past_solution=None):
        model, bookings = self.createBookingModel(solution=past_solution, ignore_piano=ignore_piano)
        self._lastBookings = bookings
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

