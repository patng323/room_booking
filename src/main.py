import random
from datetime import datetime, date
from site_booking import Site
from rmbs import Rmbs
import argparse

random.seed(1234)


def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument("--timeslots", type=int, default=24)
    # parser.add_argument("--rooms", type=int, default=50)
    # parser.add_argument("--meetings", type=int, default=20)
    parser.add_argument("--date", type=str, help="The date used to load meetings from RMBS. Format: YYYY-MM-DD", required=True)
    parser.add_argument("--ratio", help="How much of the input is used?  Mainly for testing.", type=float, default=1.0)
    parser.add_argument("--noMinWaste", help="If set, then we will skip minWaste optimization", action="store_true")
    parser.add_argument("--maxTime", help="Max. resolving time in sec", type=int, default=180)
    args = parser.parse_args()

    # We have 3 rooms (A, B and C)
    # Use edge to mark which room is next to which
    # g_rooms = networkx.Graph()
    # for rm in list(room_names):
    #    g_rooms.add_node(rm)

    # g_rooms.add_edge("A", "B")
    # g_rooms.add_edge("B", "C")

    rmbs = Rmbs()
    site = Site(rmbs, area=Rmbs.Area_Truth)

    # site.genRandomInput(num_rooms=args.rooms, num_meetings=args.meetings)
    # TODO:
    # Handle: G(地下禮堂+後區) in request
    site.load_site_info()
    site.load_existing_meetings(ratio=args.ratio, meeting_date=datetime.strptime(args.date, "%Y-%m-%d").date())
    site.load_new_requests('../data/truth_requests_20201107.csv')  # TODO: should read from forms (maybe indirectly)
    site.printConfig(print_meetings=False, print_rooms=True)

    site.basicCheck()

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
                                            and room_names[potential_noisy_room] in networkx.neighbors(g_rooms,
                                                                                                       room_names[r]):
                                        model.Add(
                                            bookings[(noisy_meeting, t, potential_noisy_room)] == False).OnlyEnforceIf(
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

    site.printConfig(print_rooms=False, print_timeslots=False)

    status, solution = site.resolve(max_time=args.maxTime, no_min_waste=args.noMinWaste)
    if status != 'INFEASIBLE':
        #site.print_one_solution(solution)
        site.export_solution(solution, "result.csv")
    else:
        print()
        print("Solve returns: " + status)

    site.printStats()
    end_time = datetime.now()
    print("end at " + str(end_time))
    print("duration: " + str(end_time - start_time))


if __name__ == "__main__":
    main()
