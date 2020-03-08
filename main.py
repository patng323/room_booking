from __future__ import print_function
import random
import string
from datetime import datetime
from rooms import Rooms
from meetings import Meetings
from bookingManager import BookingManager
from collections import defaultdict
from ortools.sat.python import cp_model

random.seed(1234)

minimizeCost = False

# We have 3 rooms (A, B and C)
# Use edge to mark which room is next to which
#g_rooms = networkx.Graph()
#for rm in list(room_names):
#    g_rooms.add_node(rm)

#g_rooms.add_edge("A", "B")
#g_rooms.add_edge("B", "C")


manager = BookingManager(name="Truth", num_timeslots=10)
manager.genRandomInput(num_rooms=22, num_meetings=3)

manager.printConfig()

if not manager.passBasicCheck():
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



# class PartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
#     """Print intermediate solutions."""
#
#     def __init__(self, bookings, sols):
#         cp_model.CpSolverSolutionCallback.__init__(self)
#         self._bookings = bookings
#         self._solutions = set(sols)
#         self._solution_count = 0
#
#     def on_solution_callback(self):
#         if self._solution_count in self._solutions:
#             print('Solution %i' % self._solution_count)
#             print_one_solution(self, self._bookings)
#             print()
#         self._solution_count += 1
#
#     def solution_count(self):
#         return self._solution_count

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

model, bookings = manager.createBookingModel()
status = solver.Solve(model)
if solver.StatusName(status) != 'INFEASIBLE':
    manager.print_one_solution(solver, bookings)
else:
    print()
    print("Solve returns: " + solver.StatusName(status))
    print("Let's try ignoring piano")
    model, bookings = manager.createBookingModel(ignore_piano=True)
    status = solver.Solve(model)
    if solver.StatusName(status) != 'INFEASIBLE':
        manager.print_one_solution(solver, bookings)

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
