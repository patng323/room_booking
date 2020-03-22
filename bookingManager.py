from __future__ import print_function
from collections import defaultdict
from rooms import Rooms
from meetings import Meetings
from ortools.sat.python import cp_model


def getid(meeting, timeslot, room):
    return meeting.name, timeslot, room.name


class BookingManager:
    CHECK_SUCCESS = 1
    CHECK_FAILED_MEETING_SIZE = -1
    CHECK_FAILED_NO_OF_MEETINGS = -2

    def __init__(self, name, num_timeslots):
        self.name = name
        self.num_timeslots = num_timeslots
        self.timeslots = list(range(num_timeslots))
        self.rooms = None
        self.meetings = None
        self.__timeslot_requests = None
        self._solver = cp_model.CpSolver()
        self._solver.parameters.linearization_level = 0
        self._lastBookings = None
        self._lastStatus = None


    def genRandomInput(self, num_rooms, num_meetings):
        self.rooms = Rooms()
        self.rooms = Rooms()
        self.rooms.genRandomInput(num_rooms)

        self.meetings = Meetings(max_meeting_size=self.rooms.max_cap)
        self.meetings.genRandomInput(num_meetings, num_timeslots=self.num_timeslots)

    @property
    def timeslot_requests(self):
        if self.__timeslot_requests is None:
            self.__timeslot_requests = defaultdict(list)

            for meeting in self.meetings:
                for t in meeting.meeting_times:
                    self.__timeslot_requests[t].append(meeting.name)

        return self.__timeslot_requests

    def printConfig(self):
        print("---------------\n")
        for meeting in self.meetings:
            piano = ''
            if meeting.needs_piano:
                piano = '(P)'
            print("Meeting {m}: size={size}{piano}, timeslots={ts}".format(
                m=meeting.name, piano=piano, size=meeting.size, ts=str(meeting.meeting_times)))
    
        print("---------------\n")
        for room in self.rooms:
            piano = ''
            if room.has_piano:
                piano = '(P)'
            print("Room {rn}: cap={cap} {piano}".format(rn=room.name, cap=room.room_cap, piano=piano))
    
        print("---------------\n")
        for t in self.timeslots:
            print("Time {t}: {ms} ({n})".format(t=t,
                            ms=[self.meetings[m].name
                                if not self.meetings[m].needs_piano
                                else "{}P".format(self.meetings[m].name)
                                for m in self.timeslot_requests[t]],
                            n=len(self.timeslot_requests[t])))
    
        print("---------------\n")

    def basicCheck(self):
        room_caps_sorted = sorted([room.room_cap for room in self.rooms], reverse=True)

        for t in self.timeslots:
            tr = self.timeslot_requests[t]
            if len(tr) > 0:
                if len(tr) > self.rooms.num_rooms:
                    print('Too many meetings (total: {}) are booked at time {}'.format(len(tr), t))
                    return self.CHECK_FAILED_NO_OF_MEETINGS, {"timeslot": t}

                sizes_sorted = sorted([(m, self.meetings[m].size) for m in tr], key=lambda x: x[1],
                                      reverse=True)
                for i in range(len(sizes_sorted)):
                    if sizes_sorted[i][1] > room_caps_sorted[i]:
                        print('Meeting {m} cannot find a fitting room (of size {s}) at time {t}'.format(
                            m=sizes_sorted[i][0], s=sizes_sorted[i][1], t=t))
                        print('Caps of all rooms: \n{}'.format(room_caps_sorted))
                        print('Sizes of meeting at time {t}: \n{s}'.format(t=t, s=str([x[1] for x in sizes_sorted])))
                        return self.CHECK_FAILED_MEETING_SIZE, {"timeslot": t}

        return self.CHECK_SUCCESS, None


    def createBookingModel(self, allocations_to_follow=None, ignore_piano=False):
        model = cp_model.CpModel()
    
        bookings = {}
        for m in self.meetings:
            for t in self.timeslots:
                for r in self.rooms:
                    # bookings[id(m, t, r] = 1 if meeting m has booked room r at time t
                    bookings[getid(m, t, r)] = model.NewBoolVar('{}'.format(getid(m, t, r)))
    
        #
        # Conditions
        #

        # If we have a set of allocations we should follow, let's set condition for them first
        if allocations_to_follow:
            for t in self.timeslots:
                for m in self.meetings:
                    for r in self.rooms:
                        if allocations_to_follow[getid(m, t, r)]:
                            model.Add(bookings[getid(m, t, r)] == 1)

        # A meeting must happen at its specified time slots
        for m in self.meetings:
            for t in self.timeslots:
                if t in m.meeting_times:
                    # if meeting m needs timeslot t, we need to book exactly one room at timeslot t
                    model.Add(sum(bookings[getid(m, t, r)] for r in self.rooms) == 1)
                else:
                    # Don't assign meeting m to any room
                    for r in self.rooms:
                        model.Add(bookings[getid(m, t, r)] == 0)
    
        # No two meetings can share the same room
        for t in self.timeslots:
            for r in self.rooms:
                # Each room can be assigned only to one meeting
                model.Add(sum(bookings[getid(m, t, r)] for m in self.meetings) <= 1)
    
        # The room capacity must fit the meeting size
        for m in self.meetings:
            for t in m.meeting_times:
                for r in self.rooms:
                    if r.room_cap < m.size:
                        model.Add(bookings[getid(m, t, r)] == 0)
    
        # A meeting must use the same room in all its required timeslots (e.g. if meeting 1 span two timeslots, then ...)
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
    
        return model, bookings

    def meetings_which_need_piano(self):
        res = []
        for m in self.meetings:
            if m.needs_piano:
                res.append(m)

        return res

    def save_one_solution(self, solver, bookings):
        allocations = {}
        for t in self.timeslots:
            for m in self.meetings:
                for r in self.rooms:
                    if solver.Value(bookings[getid(m.name, t, r.name)]):
                        allocations[getid(m.name, t, r.name)] = True

        return allocations

    def print_one_solution(self):
        booking_allocated = set()
        for t in self.timeslots:
            print('Time %i' % t)
            for m in self.meetings:
                for r in self.rooms:
                    if self._solver.Value(self._lastBookings[getid(m, t, r)]):
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
                            '  Mtg-{meeting}{mtg_times_info} (size:{mtgsize}) assigned to {room}{extra_rm} (cap:{roomcap}) '
                            '(waste={waste}) {final_info}'.format(meeting=name,
                                                     mtgsize=m.size,
                                                     room=r.name, roomcap=r.room_cap,
                                                     waste=(r.room_cap - m.size),
                                                     extra_rm=extra_rm,
                                                     mtg_times_info=mtg_times_info,
                                                     final_info=final_info
                                                     ))
        print()
        print("Meeting allocated total: {}".format(len(booking_allocated)))

    def resolve(self, ignore_piano=False):
        model, bookings = self.createBookingModel(ignore_piano=ignore_piano)
        self._lastBookings = bookings
        status = self._solver.Solve(model)
        self._lastStatus = status
        return self._solver.StatusName(status)

    def printStats(self):
        print("Solve returns: " + self._solver.StatusName(self._lastStatus))
        print()
        print('Statistics')
        print('  - conflicts       : %i' % self._solver.NumConflicts())
        print('  - branches        : %i' % self._solver.NumBranches())
        print('  - wall time       : %f s' % self._solver.WallTime())
        print()

