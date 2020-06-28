import random
from datetime import datetime
import pandas as pd
from site_booking import Site
import argparse

random.seed(1234)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeslots", type=int, default=24)
    parser.add_argument("--rooms", type=int, default=50)
    parser.add_argument("--meetings", type=int, default=20)
    args = parser.parse_args()

    minimizeCost = False

    # We have 3 rooms (A, B and C)
    # Use edge to mark which room is next to which
    #g_rooms = networkx.Graph()
    #for rm in list(room_names):
    #    g_rooms.add_node(rm)

    #g_rooms.add_edge("A", "B")
    #g_rooms.add_edge("B", "C")


    site = Site(name="truth")
    #site.genRandomInput(num_rooms=args.rooms, num_meetings=args.meetings)
    # TODO:
    # Handle: multiple rooms specified e.g. room=T1, T2
    # Handle: G(地下禮堂+後區) in request
    site.load_site_info()

    # TODO:
    # Why 週六 SATpoint 崇拜 won't be assigned to the fixed room?
    # Why 'no 2 meetings can share the same room' rule isn't working?
    site.load_meeting_requests('data/truth_fixed_20191123.csv', None, ratio=1.0)
                               #'data/truth_requests_20191123.csv')

    site.printConfig()

    res, info = site.basicCheck()
    if res != site.CHECK_SUCCESS:
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


    status, solution = site.resolve()
    if status != 'INFEASIBLE':
        site.print_one_solution(solution)
    else:
        print()
        print("Solve returns: " + status)
        print("Let's try ignoring piano for all meetings")
        print()
        status, solution = site.resolve(ignore_piano=True)
        if status != 'INFEASIBLE':
            print("It works without piano; so let's figure out which meeting is the culprit")
            print("We start by suppressing piano, starting with the smallest meeting")
            print()
            mtgs = site.meetings_which_need_piano()
            mtgs = sorted(mtgs, key=lambda mtg: mtg.size)
            for mtg in mtgs:
                mtg.suppress_piano()
                print("Suppress piano for meeting {} and try allocating:".format(mtg.name))
                try:
                    status, solution = site.resolve()
                    if status != 'INFEASIBLE':
                        site.print_one_solution(solution)
                        break
                finally:
                    mtg.suppress_piano(False)

    if status != 'INFEASIBLE':
        print("----------------------")
        print("Let's add one more room :-)")
        site.addMeeting(name="patrick", size=10, start_time=0, duration=4)
        site.printConfig(print_rooms=False, print_timeslots=False)
        status, solution = site.resolve(past_solution=solution)
        print(f"Status == {status}")
        if status != 'INFEASIBLE':
            site.print_one_solution(solution)
        print("----------------------")


    site.printStats()
    end_time = datetime.now()
    print("end at " + str(end_time))
    print("duration: " + str(end_time - start_time))

if __name__ == "__main__":
    main()

# --timeslots 10 --rooms 21 --meetings 98