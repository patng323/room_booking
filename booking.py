from __future__ import print_function
from ortools.sat.python import cp_model
import networkx


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

meeting_makeNoise = [0,0,1,1,0,0,0]
meeting_needQuiet = [0,1,0,0,0,0,0]

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
num_timeslots = 7
num_rooms = 3

all_meetings = range(num_meetings)
all_timeslots = range(num_timeslots)
all_rooms = range(num_rooms)

all_noisy_meetings = list(filter(lambda i: meeting_makeNoise[i] == 1, range(num_meetings)))
all_quiet_meetings = list(filter(lambda i: meeting_needQuiet[i] == 1, range(num_meetings)))

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
for m in all_meetings:
    for t in meeting_times[m]:
        for r in all_rooms:
            if meeting_needs_piano[m] == 1 and room_has_piano[r] == 0:
                model.Add(bookings[(m, t, r)] == 0)  # if the room as no piano, don't assign

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


# Minimize room cap wastage
minimizeCost=True
model.Minimize(sum((room_cap[r] - meeting_sizes[m]) * bookings[(m, t, r)]
               for m in all_meetings for t in all_timeslots for r in all_rooms))


def print_one_solution(solver, bookings):
    for t in all_timeslots:
        print('Time %i' % t)
        for m in all_meetings:
            for r in all_rooms:
                if solver.Value(bookings[(m, t, r)]):
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

if not minimizeCost:
    # Display the first five solutions.
    a_few_solutions = range(5)
    solution_printer = PartialSolutionPrinter(bookings, a_few_solutions)
    solver.SearchForAllSolutions(model, solution_printer)
else:
    status = solver.Solve(model)
    print("Solve returns: " + solver.StatusName(status))
    if solver.StatusName(status) != 'INFEASIBLE':
        print_one_solution(solver, bookings)

