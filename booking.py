from __future__ import print_function
from ortools.sat.python import cp_model
import random
import string
from datetime import datetime
from rooms import Rooms
from meetings import Meetings
from location import Location
from collections import defaultdict

random.seed(1234)

minimizeCost = False

# We have 3 rooms (A, B and C)
# Use edge to mark which room is next to which
#g_rooms = networkx.Graph()
#for rm in list(room_names):
#    g_rooms.add_node(rm)

#g_rooms.add_edge("A", "B")
#g_rooms.add_edge("B", "C")


def printConfig(location, rooms, meetings):
    timeslot_requests = defaultdict(list)

    print("---------------\n")
    for meeting in meetings:
        piano = ''
        if meeting.needs_piano:
            piano = '(P)'
        print("Meeting {m}: size={size}{piano}, timeslots={ts}".format(
            m=meeting.name, piano=piano, size=meeting.size, ts=str(meeting.meeting_times)))

        for t in meeting.meeting_times:
            timeslot_requests[t].append(meeting.name)

    print("---------------\n")
    for room in rooms:
        piano = ''
        if room.has_piano:
            piano = '(P)'
        print("Room {rn}: cap={cap} {piano}".format(rn=room.name, cap=room.room_cap, piano=piano))

    print("---------------\n")
    for t in location.timeslots:
        print("Time {t}: {ms}".format(t=t, ms=str(timeslot_requests[t])))

    print("---------------\n")


def passBasicCheck(location, rooms, meetings):
    for t in location.timeslots:
        meeting_request = 0
        for meeting in meetings:
            if t in meeting.meeting_times:
                meeting_request += 1

        if meeting_request > rooms.num_rooms:
            print('Too many meetings (total: {}) are booked at time {}'.format(meeting_request, t))
            return False

    return True


def getid(meeting, timeslot, room):
    return (meeting.name, timeslot, room.name)


def createBookingModel(location, rooms, meetings, ignore_piano=False):
    model = cp_model.CpModel()

    bookings = {}
    for m in meetings:
        for t in location.timeslots:
            for r in rooms:
                # bookings[id(m, t, r] = 1 if meeting m has booked room r at time t
                print("Add var: {}".format(getid(m, t, r)))
                bookings[getid(m, t, r)] = model.NewBoolVar('{}'.format(getid(m, t, r)))

    #
    # Conditions
    #

    # A meeting must happen at its specified time slots
    for m in meetings:
        for t in location.timeslots:
            if t in m.meeting_times:
                # if meeting m needs timeslot t, we need to book exactly one room at timeslot t
                model.Add(sum(bookings[getid(m, t, r)] for r in rooms) == 1)
            else:
                # Don't assign meeting m to any room
                for r in rooms:
                    model.Add(bookings[getid(m, t, r)] == 0)

    # No two meetings can share the same room
    for t in location.timeslots:
        for r in rooms:
            # Each room can be assigned only to one meeting
            model.Add(sum(bookings[getid(m, t, r)] for m in meetings) <= 1)

    # The room capacity must fit the meeting size
    for m in meetings:
        for t in m.meeting_times:
            for r in rooms:
                if r.room_cap < m.size:
                    model.Add(bookings[getid(m, t, r)] == 0)

    # A meeting must use the same room in all its required timeslots (e.g. if meeting 1 span two timeslots, then ...)
    for m in meetings:
        for r in rooms:
            for i in range(len(m.meeting_times) - 1):
                # For room r, if the current timeslot is TRUE, then the next one must be true too
                model.Add(bookings[getid(m, m.meeting_times[i + 1], r)]).OnlyEnforceIf(
                    bookings[getid(m, m.meeting_times[i], r)])

    if not ignore_piano:
        # A room which requires piano must use a room that has a piano
        for m in meetings:
            for t in m.meeting_times:
                for r in rooms:
                    if m.needs_piano and not r.has_piano:
                        model.Add(bookings[getid(m, t, r)] == 0)  # if the room as no piano, don't assign

    return model, bookings


location = Location(name="Truth", num_timeslots=10)

rooms = Rooms()
rooms.genRandomInput(num_rooms=22)

meetings = Meetings(max_meeting_size=rooms.max_cap)
meetings.genRandomInput(num_meetings=10, num_timeslots=location.num_timeslots)

printConfig(location, rooms, meetings)

if not passBasicCheck(location, rooms, meetings):
    exit(1)

if False:
    all_noisy_meetings = list(filter(lambda i: meeting_makeNoise[i] == 1, range(num_meetings)))
    all_quiet_meetings = list(filter(lambda i: meeting_needQuiet[i] == 1, range(num_meetings)))

    # A room which makes noise shouldn't be next to a room which needs quietness
    for m in all_quiet_meetings:
        for t in m.meeting_times:
            for noisy_meeting in all_noisy_meetings:
                # Check if these two meetings will happen at the same time
                if t in meeting_times[noisy_meeting]:
                    for r in rooms:
                        if r.room_cap >= m.size:
                            for potential_noisy_room in rooms:
                                if potential_noisy_room != r \
                                        and room_cap[potential_noisy_room] >= meeting_sizes[noisy_meeting] \
                                        and room_names[potential_noisy_room] in networkx.neighbors(g_rooms, room_names[r]):
                                    model.Add(bookings[(noisy_meeting, t, potential_noisy_room)] == False).OnlyEnforceIf(
                                        bookings[(m.name, t, r.name)]
                                    )


def print_one_solution(solver, bookings, location, rooms, meetings):
    booking_allocated = set()
    for t in location.timeslots:
        print('Time %i' % t)
        for m in meetings:
            for r in rooms:
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
                    print('  Mtg-{meeting}{mtg_times_info} (size:{mtgsize}{extra}) assigned to room {room}{extra_rm} (cap:{roomcap}) '
                          '(waste={waste})'.format(meeting=m.name,
                                                   mtgsize=m.size, extra=extra,
                                                   room=r.name, roomcap=r.room_cap,
                                                   waste=(r.room_cap - m.size),
                                                   extra_rm=extra_rm,
                                                   mtg_times_info=mtg_times_info
                                                   ))
    print()
    print("Meeting allocated total: {}".format(len(booking_allocated)))

class PartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, bookings, sols):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._bookings = bookings
        self._solutions = set(sols)
        self._solution_count = 0

    def on_solution_callback(self):
        if self._solution_count in self._solutions:
            print('Solution %i' % self._solution_count)
            print_one_solution(self, self._bookings)
            print()
        self._solution_count += 1

    def solution_count(self):
        return self._solution_count

solver = cp_model.CpSolver()
solver.parameters.linearization_level = 0

start_time = datetime.now()
print("start at " + str(start_time))

if False:
    # Display the first five solutions.
    a_few_solutions = range(1)
    solution_printer = PartialSolutionPrinter(bookings, a_few_solutions)
    solver.SearchForAllSolutions(model, solution_printer)

# Minimize room cap wastage
#model.Minimize(sum((r.room_cap - m.size) * bookings[(m.name, t, r.name)]
#                   for m in meetings for t in all_timeslots for r in rooms))

model, bookings = createBookingModel(location, rooms, meetings)
status = solver.Solve(model)
if solver.StatusName(status) != 'INFEASIBLE':
    print_one_solution(solver, bookings)
else:
    print()
    print("Solve returns: " + solver.StatusName(status))
    print("Let's try ignoring piano")
    model, bookings = createBookingModel(location, rooms, meetings, ignore_piano=True)
    status = solver.Solve(model)
    if solver.StatusName(status) != 'INFEASIBLE':
        print_one_solution(solver, bookings)

end_time = datetime.now()

print("Solve returns: " + solver.StatusName(status))
print()
print('Statistics')
print('  - conflicts       : %i' % solver.NumConflicts())
print('  - branches        : %i' % solver.NumBranches())
print('  - wall time       : %f s' % solver.WallTime())
print()

print("end at " + str(end_time))
print("duration: " + str(end_time - start_time))
