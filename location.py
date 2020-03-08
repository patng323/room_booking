from __future__ import print_function
from collections import defaultdict

class Location:
    def __init__(self, name, num_timeslots):
        self.name = name
        self.num_timeslots = num_timeslots
        self.timeslot_requests = defaultdict(list)
        self.timeslots = list(range(num_timeslots))

