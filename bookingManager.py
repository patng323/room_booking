from __future__ import print_function
from collections import defaultdict
from rooms import Rooms
from meetings import Meetings
from ortools.sat.python import cp_model


def getid(meeting, timeslot, room):
    return meeting.name, timeslot, room.name


class BookingManager:
    def __init__(self, name, num_timeslots):
        self.name = name
        self.num_timeslots = num_timeslots
        self.timeslots = list(range(num_timeslots))
        self.rooms = None
        self.meetings = None
        self.__timeslot_requests = None

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
            print("Time {t}: {ms}".format(t=t, ms=str(self.timeslot_requests[t])))
    
        print("---------------\n")


    def passBasicCheck(self):
        for t in self.timeslots:
            meeting_request = 0
            for meeting in self.meetings:
                if t in meeting.meeting_times:
                    meeting_request += 1
    
            if meeting_request > self.rooms.num_rooms:
                print('Too many meetings (total: {}) are booked at time {}'.format(meeting_request, t))
                return False
    
        return True

    def createBookingModel(self, ignore_piano=False):
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

    def print_one_solution(self, solver, bookings):
        booking_allocated = set()
        for t in self.timeslots:
            print('Time %i' % t)
            for m in self.meetings:
                for r in self.rooms:
                    if solver.Value(bookings[(m.name, t, r.name)]):
                        booking_allocated.add(m.name)
                        extra = extra_rm = mtg_times_info = ''
                        if m.needs_piano:
                            extra = ", piano"

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
                            '  Mtg-{meeting}{mtg_times_info} (size:{mtgsize}{extra}) assigned to room {room}{extra_rm} (cap:{roomcap}) '
                            '(waste={waste})'.format(meeting=m.name,
                                                     mtgsize=m.size, extra=extra,
                                                     room=r.name, roomcap=r.room_cap,
                                                     waste=(r.room_cap - m.size),
                                                     extra_rm=extra_rm,
                                                     mtg_times_info=mtg_times_info
                                                     ))
        print()
        print("Meeting allocated total: {}".format(len(booking_allocated)))

