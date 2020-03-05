from __future__ import print_function
from ortools.sat.python import cp_model
import networkx
import random
import string
from datetime import datetime
import collections

random.seed(1234)

minimizeCost = False

meeting_sizes = [4, 5, 2, 10, 4, 2, 4]
meeting_needs_piano = [1, 0, 0, 0, 0, 1, 0]

meeting_times = [
    [0],    # meeting 1
    [1],    # meeting 2
    [1, 2, 3, 4], # meeting 3
    [3],    # meeting 4
    [4],    # meeting 5
    [4, 5], # meeting 6
    [5, 6]  # meeting 7
]

meeting_makeNoise = [0, 0, 1, 1, 0, 0, 0]
meeting_needQuiet = [0, 1, 0, 0, 0, 0, 0]

room_cap = [2, 10, 6]
room_has_piano = [0, 1, 0]
room_names = "ABC"

# We have 3 rooms (A, B and C)
# Use edge to mark which room is next to which
g_rooms = networkx.Graph()
for rm in list(room_names):
    g_rooms.add_node(rm)

g_rooms.add_edge("A", "B")
g_rooms.add_edge("B", "C")

num_meetings = len(meeting_sizes)
num_timeslots = 10
num_rooms = len(room_cap)


def genRandomInput():
    global room_cap, room_names, meeting_sizes, meeting_times, num_rooms, num_meetings, \
        room_has_piano, meeting_needs_piano

    num_rooms = 20
    num_meetings = 50

    room_cap = []
    room_has_piano = []
    for i in range(num_rooms):
        room_cap.append(random.randint(8, 12))
        rn = random.randint(1, 100)
        if rn >= 70:
            room_has_piano.append(1)
        else:
            room_has_piano.append(0)

    room_names = string.ascii_uppercase[0:num_rooms]

    max_cap = max(room_cap)

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

        if rn >= 95:
            meeting_needs_piano.append(1)
        else:
            meeting_needs_piano.append(0)

        end_time = min(duration + start_time - 1, num_timeslots - 1)
        meeting_times.append(list(range(start_time, end_time+1)))


genRandomInput()


all_meetings = range(num_meetings)
all_timeslots = range(num_timeslots)
all_rooms = range(num_rooms)

print("Total # of meetings: {}".format(num_meetings))
print()

timeslot_requests = {}
for t in all_timeslots:
    timeslot_requests[t] = list()

for m in all_meetings:
    print("Meeting {m}: size={size}, timeslots={ts}".format(m=m,
                                                            size=meeting_sizes[m], ts=str(meeting_times[m])))
    for t in meeting_times[m]:
        timeslot_requests[t].append(m)

print("---------------\n")
for r in all_rooms:
    print("Room {rn}: cap={cap}".format(rn=room_names[r], cap=room_cap[r]))

print("---------------\n")
for t in all_timeslots:
    print("Time {t}: {ms}".format(t=t, ms=str(timeslot_requests[t])))

print("---------------\n")

# Create the variables
model = cp_model.CpModel()
bookings = {}
for m in all_meetings:
    for t in all_timeslots:
        for r in all_rooms:
            # bookings[(m, t, r)] = 1 if meeting m has booked room r at time t
            bookings[(m, t, r)] = model.NewBoolVar('booking_mtg-{}_time-{}_room-{}'.format(m+1, t, room_names[r]))

#
# Conditions
#

# A meeting must happen at its specified time slots
for m in all_meetings:
    for t in all_timeslots:
        if t in meeting_times[m]:
            model.Add(sum(bookings[(m, t, r)] for r in all_rooms) == 1)
        else:
            # For other timeslots, don't assign the meeting to any room
            for r in all_rooms:
                model.Add(bookings[(m, t, r)] == 0)

# No two meetings can share the same room
for t in all_timeslots:
    for r in all_rooms:
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
            # For room r, if the current timeslot if TRUE, then the next one must be true too
            model.Add(bookings[(m, meeting_times[m][i+1], r)] == True).OnlyEnforceIf(bookings[(m, meeting_times[m][i], r)])

# A room which requires piano must use the suitable room
if True:
    for m in all_meetings:
        for t in meeting_times[m]:
            for r in all_rooms:
                if meeting_needs_piano[m] == 1 and room_has_piano[r] == 0:
                    model.Add(bookings[(m, t, r)] == 0)  # if the room as no piano, don't assign

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

def print_one_solution_v2(solver, bookings):
    booking_allocated = set()
    for t in all_timeslots:
        print('Time %i' % t)
        for m in all_meetings:
            for r in all_rooms:
                if solver.Value(bookings[(m, t, r)]):
                    booking_allocated.add(m)
                    extra = extra_rm = ''
                    if meeting_needs_piano[m]:
                        extra = ", needs piano"

                    if room_has_piano[r]:
                        extra_rm = 'P'

                    if extra_rm:
                        extra_rm = '(' + extra_rm + ')'
                    print('  Mtg-{meeting} (size:{mtgsize}{extra}) assigned to room {room}{extra_rm} (cap:{roomcap}) '
                          '(waste={waste})'.format(meeting=m + 1,
                                                   mtgsize=meeting_sizes[m], extra=extra,
                                                   room=room_names[r], roomcap=room_cap[r],
                                                   waste=(room_cap[r] - meeting_sizes[m]),
                                                   extra_rm=extra_rm))
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
minimizeCost = True

if False:
    # Display the first five solutions.
    a_few_solutions = range(1)
    solution_printer = PartialSolutionPrinter(bookings, a_few_solutions)
    solver.SearchForAllSolutions(model, solution_printer)
else:
    # Minimize room cap wastage
    #model.Minimize(sum((room_cap[r] - meeting_sizes[m]) * bookings[(m, t, r)]
    #                   for m in all_meetings for t in all_timeslots for r in all_rooms))

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
