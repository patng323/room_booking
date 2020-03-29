import unittest

import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from util import Util
from datetime import datetime


class TestUtil(unittest.TestCase):
    def test_parse_time_field(self):
        self.assertTupleEqual(Util.parse_time_field("上午09:30 - 上午10:30"),
                              (datetime(1900, 1, 1, 9, 30), datetime(1900, 1, 1, 10, 30)), "AM to AM")

        self.assertTupleEqual(Util.parse_time_field("上午09:30 - 下午01:30"),
                              (datetime(1900, 1, 1, 9, 30), datetime(1900, 1, 1, 13, 30)), "AM to PM")

        self.assertTupleEqual(Util.parse_time_field("上午09:30 - 下午12:00"),
                              (datetime(1900, 1, 1, 9, 30), datetime(1900, 1, 1, 12, 00)), "AM to Noon")

        self.assertTupleEqual(Util.parse_time_field("上午09:30 - 下午12:30"),
                              (datetime(1900, 1, 1, 9, 30), datetime(1900, 1, 1, 12, 30)), "AM to past Noon")

        self.assertTupleEqual(Util.parse_time_field("下午12:00 - 下午12:30"),
                              (datetime(1900, 1, 1, 12, 00), datetime(1900, 1, 1, 12, 30)), "Noon to past Noon")

        self.assertTupleEqual(Util.parse_time_field("下午12:00 - 下午01:30"),
                              (datetime(1900, 1, 1, 12, 00), datetime(1900, 1, 1, 13, 30)), "Noon to PM")

        self.assertTupleEqual(Util.parse_time_field("下午01:00 - 下午02:30"),
                              (datetime(1900, 1, 1, 13, 00), datetime(1900, 1, 1, 14, 30)), "PM to PM")

        # English
        self.assertTupleEqual(Util.parse_time_field("09:30am - 12:30pm"),
                              (datetime(1900, 1, 1, 9, 30), datetime(1900, 1, 1, 12, 30)), "AM to past Noon")

        self.assertTupleEqual(Util.parse_time_field("01:00pm - 02:30pm"),
                              (datetime(1900, 1, 1, 13, 00), datetime(1900, 1, 1, 14, 30)), "PM to PM")




if __name__ == '__main__':
    unittest.main()

