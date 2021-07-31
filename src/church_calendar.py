from datetime import date, timedelta, datetime


def earliest_booking_date(register_time: datetime):
    # TODO: Need to consider Church calendar
    # Users can only book max of 3 “教會 working” days in advance
    # - Today: Nov 1st
    # - Before 2:30pm, a user can book Nov 4th or after
    # - After 2:30pm a user can only book Nov 5th or after

    # register_time == 交 Form 時間
    days = 3
    if register_time.strftime('%H%M') >= '1431':
        days += 1

    # Applicants cannot book any date BEFORE earliest booking date
    earliest = register_time + timedelta(days=days)
    return date(year=earliest.year, month=earliest.month, day=earliest.day)
