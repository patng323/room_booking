from __future__ import print_function
from ortools.sat.python import cp_model
import networkx
import random
import string
from datetime import datetime
import collections

random.seed(1234)

minimizeCost = False

# We have 3 rooms (A, B and C)
# Use edge to mark which room is next to which
#g_rooms = networkx.Graph()
#for rm in list(room_names):
#    g_rooms.add_node(rm)

#g_rooms.add_edge("A", "B")
#g_rooms.add_edge("B", "C")


def genRandomInput(num_rooms=20, num_meetings=70, num_timeslots=10):
    room_cap = []
    room_has_piano = []
    meeting_needs_piano = []

    room_names = string.ascii_uppercase[0:num_rooms]

    for i in range(num_rooms):
        cap = random.randint(8, 12)
        room_cap.append(cap)

    max_cap = max(room_cap)
    for i in range(num_rooms):
        if room_cap[i] >= (max_cap - 3):
            room_has_piano.append(1)
        else:
            room_has_piano.append(0)

    meeting_sizes = []
    meeting_times = []
    for i in range(num_meetings):
        meeting_sizes.append(random.randint(2, max_cap))
        start_time = random.randint(0, num_timeslots-1)
        rn = random.randint(1, 100)
        if rn <= 50:
            duration = 1
        elif rn <= 90:
            duration = 2
        else:
            duration = 3

        if random.randint(1, 100) >= 80:
            meeting_needs_piano.append(1)
        else:
            meeting_needs_piano.append(0)

        end_time = min(duration + start_time - 1, num_timeslots - 1)
        meeting_times.append(list(range(start_time, end_time+1)))

    return room_cap, room_names, meeting_sizes, meeting_times, room_has_piano, meeting_needs_piano


def genDataLists(num_meetings, num_timeslots, num_rooms, meeting_sizes, meeting_times):
    all_meetings = range(num_meetings)
    all_timeslots = range(num_timeslots)
    all_rooms = range(num_rooms)

    timeslot_requests = {}
    for t in all_timeslots:
        timeslot_requests[t] = list()

    for m in all_meetings:
        for t in meeting_times[m]:
            timeslot_requests[t].append(m)

    return all_meetings, all_timeslots, all_rooms, timeslot_requests


def printConfig(all_rooms, room_names, room_cap, all_timeslots, timeslot_requests,
                all_meetings, meeting_needs_piano):
    print("---------------\n")
    for m in all_meetings:
        piano = ''
        if meeting_needs_piano[m] == 1:
            piano = '(P)'
        print("Meeting {m}: size={size}{piano}, timeslots={ts}".format(m=m, piano=piano,
                                                                size=meeting_sizes[m], ts=str(meeting_times[m])))
        for t in meeting_times[m]:
            timeslot_requests[t].append(m)

    print("---------------\n")
    for r in all_rooms:
        piano = ''
        if room_has_piano[r] == 1:
            piano = '(P)'
        print("Room {rn}: cap={cap} {piano}".format(rn=room_names[r], cap=room_cap[r], piano=piano))

    print("---------------\n")
    for t in all_timeslots:
        print("Time {t}: {ms}".format(t=t, ms=str(timeslot_requests[t])))

    print("---------------\n")


def passBasicCheck(all_timeslots, all_meetings, meeting_times, num_rooms):
    for t in all_timeslots:
        meeting_request = 0
        for m in all_meetings:
            if t in meeting_times[m]:
                meeting_request += 1

        if meeting_request > num_rooms:
            print('Too many meetings (total: {}) are booked at time {}'.format(meeting_request, t))
            return False

    return True


def createBookingModel(all_meetings, all_timeslots, all_rooms, meeting_times, ignore_piano=False):
    model = cp_model.CpModel()

    bookings = {}
    for m in all_meetings:
        for t in all_timeslots:
            for r in all_rooms:
                # bookings[(m, t, r)] = 1 if meeting m has booked room r at time t
                bookings[(m, t, r)] = model.NewBoolVar('mtg-{}_time-{}_room-{}'.format(m + 1, t, room_names[r]))

    #
    # Conditions
    #

    # A meeting must happen at its specified time slots
    for m in all_meetings:
        for t in all_timeslots:
            if t in meeting_times[m]:
                # if meeting m needs timeslot t, we need to book exactly one room at timeslot t
                model.Add(sum(bookings[(m, t, r)] for r in all_rooms) == 1)
            else:
                # Don't assign meeting m to any room
                for r in all_rooms:
                    model.Add(bookings[(m, t, r)] == 0)

    # No two meetings can share the same room
    for t in all_timeslots:
        for r in all_rooms:
            # Each room can be assigned only to one meeting
            model.Add(sum(bookings[(m, t, r)] for m in all_meetings) <= 1)

    # The room capacity must fit the meeting size
    for m in all_meetings:
        for t in meeting_times[m]:
            for r in all_rooms:
                if room_cap[r] < meeting_sizes[m]:
                    model.Add(bookings[(m, t, r)] == 0)

    # A meeting must use the same room in all its required timeslots (e.g. if meeting 1 span two timeslots, then ...)
    for m in all_meetings:
        for r in all_rooms:
            for i in range(len(meeting_times[m]) - 1):
                # For room r, if the current timeslot is TRUE, then the next one must be true too
                model.Add(bookings[(m, meeting_times[m][i + 1], r)] == True).OnlyEnforceIf(
                    bookings[(m, meeting_times[m][i], r)])

    if not ignore_piano:
        # A room which requires piano must use a room that has a piano
        for m in all_meetings:
            for t in meeting_times[m]:
                for r in all_rooms:
                    if meeting_needs_piano[m] == 1 and room_has_piano[r] == 0:
                        model.Add(bookings[(m, t, r)] == 0)  # if the room as no piano, don't assign

    return model, bookings


num_rooms = 22
num_meetings = 110
num_timeslots = 10

room_cap, room_names, meeting_sizes, meeting_times, room_has_piano, meeting_needs_piano = \
    genRandomInput(num_rooms, num_meetings, num_timeslots)

all_meetings, all_timeslots, all_rooms, timeslot_requests = genDataLists(num_meetings, num_timeslots,
                                                                         num_rooms, meeting_sizes, meeting_times)

printConfig(all_rooms, room_names, room_cap, all_timeslots, timeslot_requests,
            all_meetings, meeting_needs_piano)

if not passBasicCheck(all_timeslots, all_meetings, meeting_times, num_rooms):
    exit(1)

if False:
    all_noisy_meetings = list(filter(lambda i: meeting_makeNoise[i] == 1, range(num_meetings)))
    all_quiet_meetings = list(filter(lambda i: meeting_needQuiet[i] == 1, range(num_meetings)))

    # A room which makes noise shouldn't be next to a room which needs quietness
    for m in all_quiet_meetings:
        for t in meeting_times[m]:
            for noisy_meeting in all_noisy_meetings:
                # Check if these two meetings will happen at the same time
                if t in meeting_times[noisy_meeting]:
                    for r in all_rooms:
                        if room_cap[r] >= meeting_sizes[m]:
                            for potential_noisy_room in all_rooms:
                                if potential_noisy_room != r \
                                        and room_cap[potential_noisy_room] >= meeting_sizes[noisy_meeting] \
                                        and room_names[potential_noisy_room] in networkx.neighbors(g_rooms, room_names[r]):
                                    model.Add(bookings[(noisy_meeting, t, potential_noisy_room)] == False).OnlyEnforceIf(
                                        bookings[(m, t, r)]
                                    )


def print_one_solution(solver, bookings):
    booking_allocated = set()
    for t in all_timeslots:
        print('Time %i' % t)
        for m in all_meetings:
            for r in all_rooms:
                if solver.Value(bookings[(m, t, r)]):
                    booking_allocated.add(m)
                    extra = extra_rm = mtg_times_info = ''
                    if meeting_needs_piano[m]:
                        extra = ", piano"

                    if room_has_piano[r]:
                        extra_rm = 'P'

                    if len(meeting_times[m]) > 1:
                        if meeting_times[m][0] == t:
                            mtg_times_info = '*'
                        else:
                            mtg_times_info = '.'

                    if extra_rm:
                        extra_rm = '(' + extra_rm + ')'
                    print('  Mtg-{meeting}{mtg_times_info} (size:{mtgsize}{extra}) assigned to room {room}{extra_rm} (cap:{roomcap}) '
                          '(waste={waste})'.format(meeting=m + 1,
                                                   mtgsize=meeting_sizes[m], extra=extra,
                                                   room=room_names[r], roomcap=room_cap[r],
                                                   waste=(room_cap[r] - meeting_sizes[m]),
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
#model.Minimize(sum((room_cap[r] - meeting_sizes[m]) * bookings[(m, t, r)]
#                   for m in all_meetings for t in all_timeslots for r in all_rooms))

model, bookings = createBookingModel(all_meetings, all_timeslots, all_rooms, meeting_times)
status = solver.Solve(model)
if solver.StatusName(status) != 'INFEASIBLE':
    print_one_solution(solver, bookings)
else:
    print()
    print("Solve returns: " + solver.StatusName(status))
    print("Let's try ignoring piano")
    model, bookings = createBookingModel(all_meetings, all_timeslots, all_rooms, meeting_times, ignore_piano=True)
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
