import random
from datetime import datetime, date
from site_booking import Site
from rmbs import Rmbs
import argparse
import logging
from util import Util
from applications import Applications
import pandas as pd

random.seed(1234)

Util.setup_logging()
logger = logging.getLogger(__name__)

_debug = False

def main2():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="The date used to load meetings from RMBS. Format: YYYY-MM-DD", required=True)
    parser.add_argument("--noMinWaste", help="If set, then we will skip minWaste optimization", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--maxTime", help="Max. resolving time in sec", type=int, default=600)
    args = parser.parse_args()

    _debug = args.debug

    # We have 3 rooms (A, B and C)
    # Use edge to mark which room is next to which
    # g_rooms = networkx.Graph()
    # for rm in list(room_names):
    #    g_rooms.add_node(rm)

    # g_rooms.add_edge("A", "B")
    # g_rooms.add_edge("B", "C")

    rmbs = Rmbs()

    applications = Applications.get_applications()
    if not applications:
        logger.info("No application found")
        return

    df_apps = pd.DataFrame(applications)
    grouped_apps = df_apps.groupby(['eventSite', 'eventDate'])
    for group_name, df_group in grouped_apps:
        process_site_applications(area=group_name[0], rmbs=rmbs, event_date=group_name[1], apps=df_group,
                                  max_resolve_time=args.maxTime, no_min_waste=args.noMinWaste)

    Applications.update_job_info(applications)


def process_site_applications(area: str, rmbs: Rmbs, event_date: date, apps: pd.DataFrame,
                              max_resolve_time=600, no_min_waste=False):
    logger.info(f'Processing: area={area}, date={event_date}')
    site = Site(rmbs, area=Rmbs.Areas[area])

    # TODO:
    # Handle: G(地下禮堂+後區) in request
    site.load_site_info()
    site.load_existing_meetings(meeting_date=event_date)

    # TODO: should read from forms (maybe indirectly)
    #site.load_new_requests('../data/truth_requests_20201107.csv')
    site.load_new_requests(df_requests=apps)

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

    start_time = datetime.now()
    logging.info(f"start at {start_time}")
    #site.printConfig(print_rooms=False, print_timeslots=False)

    status, solution = site.resolve(max_time=max_resolve_time, no_min_waste=no_min_waste)
    if status != 'INFEASIBLE':
        if _debug:
            site.print_one_solution(solution)
            site.export_solution(solution, "result.csv")

        df_new_bookings, new_meeting_ids = site.export_new_bookings(
            solution,
            filename="result_new_booking.csv" if _debug else None,
            write_to_db=True)
        site.send_new_bookings_email(df_new_bookings)
        logging.info(f'new meeting ids: {new_meeting_ids}')

    else:
        logging.info("Solve returns: " + status)
        site.send_no_solution_email()

    site.printStats()
    end_time = datetime.now()
    logging.info(f"end at {end_time}; duration: {end_time - start_time}")


if __name__ == "__main__":
    main2()
