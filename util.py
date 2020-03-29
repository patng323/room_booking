# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta

class Util:
    @staticmethod
    def parse_time_field(time_field: str):
        time_field = time_field.replace(" ", "")
        time_field = time_field.replace("：", ":")  # Replace the chinese colon by the standard one
        parts = time_field.split("-")
        assert len(parts) == 2

        parts_time = []

        for part in parts:
            pm = False
            part = part.lower()
            m = re.search("am|pm|上午|下午", part)
            if m:
                if m.group() in ["pm", "下午"]:
                    pm = True

                part = part.replace(m.group(), "")

            part_time = datetime.strptime(part, "%H:%M")
            if pm:
                assert part_time.hour <= 12
                if part_time.hour != 12:
                    # Note: 12pm is a special case, where we don't need to adjust the time
                    part_time += timedelta(hours=12)

            parts_time.append(part_time)

        return parts_time[0], parts_time[1]






