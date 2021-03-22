import yaml
from sqlalchemy import create_engine
from pymysql import connect
import os
import csv
import pandas as pd
from datetime import datetime, date, timedelta
import re
import logging
from util import Util

logger = logging.getLogger(__name__)

_queries = {
    "mrbs_area": '''
SELECT id, CONVERT(BINARY CONVERT(area_name USING latin1) USING utf8) as area_name, area_admin_email
FROM mrbs.mrbs_area ''',

    "mrbs_entry": '''
select 
id,start_time,end_time,entry_type,repeat_id,room_id,timestamp,create_by,
CONVERT(BINARY CONVERT(name USING latin1) USING utf8) as name,
type,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description
from mrbs_entry ''',

    "mrbs_entry_join_room": '''
select 
e.id, e.start_time, e.end_time, e.entry_type, e.repeat_id, e.room_id, e.timestamp, e.create_by,
CONVERT(BINARY CONVERT(e.name USING latin1) USING utf8) as name,
e.type,
CONVERT(BINARY CONVERT(e.description USING latin1) USING utf8) as description,
CONVERT(BINARY CONVERT(r.room_name USING latin1) USING utf8) as room
from mrbs_entry e join mrbs_room r on e.room_id = r.id ''',

    "mrbs_room": '''
SELECT 
id,area_id,room_zone,room_group,
CONVERT(BINARY CONVERT(room_name USING latin1) USING utf8) as room_name,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description,
CONVERT(BINARY CONVERT(equipment USING latin1) USING utf8) as equipment,
capacity,room_admin_email
FROM mrbs.mrbs_room ''',

    "mrbs_repeat": '''
SELECT
id,start_time,end_time,rep_type,end_date,rep_opt,room_id,timestamp,create_by,
CONVERT(BINARY CONVERT(name USING latin1) USING utf8) as name,
type,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description,
rep_num_weeks,rep_spec_week,rep_date
FROM mrbs.mrbs_repeat ''',

    "mrbs_facility_type": '''
SELECT 
id, CONVERT(BINARY CONVERT(type USING latin1) USING utf8) as type, area_id 
FROM mrbs_facility_type ''',

    "mrbs_facility_with_names": '''
SELECT f.id, f.room_id, f.area_id, CONVERT(BINARY CONVERT(r.room_name USING latin1) USING utf8) as room_name, 
facility_type_id, CONVERT(BINARY CONVERT(ft.type USING latin1) USING utf8) as facility
FROM mrbs_facility f JOIN mrbs_facility_type ft on f.facility_type_id=ft.id
JOIN mrbs_room r on f.room_id = r.id
    '''
}


def _to_epoch(dt):
    if type(dt) == date:
        dt = datetime(year=dt.year, month=dt.month, day=dt.day)

    return int(dt.timestamp())


class Rmbs:
    # 1: 康澤
    # 2: 真理樓
    # 3: 教育樓（X)
    # 4: 恩典樓
    # 6: 教育樓
    # 7: 真理樓 2021

    Area_Hong = 1
    Area_Truth = 2
    Area_Grace = 4
    Area_Edu = 6
    Area_Truth2021 = 7

    def __init__(self):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)["db"]
            self.host = config['host']
            self.user = config['user']
            self.password = config['password']
            self.database = config['database']

    def test(self):
        connection = connect(host=self.host, user=self.user, password=self.password, db=self.database, charset='utf8')
        with connection.cursor() as cursor:
            start_time = _to_epoch(datetime.strptime("2020-12-13 10:00:00", "%Y-%m-%d %H:%M:%S"))
            end_time = _to_epoch(datetime.strptime("2020-12-13 10:30:00", "%Y-%m-%d %H:%M:%S"))
            name = "大食會's 時間！"
            description = "係咁食\n之後就太飽了."
            # Create a new record
            query = f'''
INSERT INTO mrbs_entry (start_time, end_time, entry_type, repeat_id, room_id, create_by, name, type, description)
VALUES ({start_time}, {end_time}, 0, 0, 202,
'administrator', convert(_latin1%s using utf8), 'I', convert(_latin1%s using utf8))'''
            cursor.execute(query, (name, description))
            print(f'id={cursor.lastrowid}')

        connection.commit()

    def _sqlEngine(self):
        return create_engine(f'mysql+pymysql://{self.user}:{self.password}@{self.host}/{self.database}?charset=utf8',
                             pool_recycle=3600)

    def read_areas(self):
        dbConnection = self._sqlEngine().connect()
        try:
            frame = pd.read_sql(_queries['mrbs_area'], dbConnection)
            pd.set_option('display.expand_frame_repr', False)
            print(frame)
        finally:
            dbConnection.close()

    @staticmethod
    def _massage_room_name(name):
        # Massage room name.  E.g. T 1 --> T1
        return re.sub(r'^([A-Z]) (\d{1,2})$', r'\g<1>\g<2>', name).strip()
        
    def read_rooms(self, area: int):
        dbConnection = self._sqlEngine().connect()
        try:
            # If capacity==0, we still read them; but they won't use them during auto-allocation due to its size
            df = pd.read_sql(_queries['mrbs_room'] + f'where area_id={area} order by room_name, capacity', dbConnection)
            df['room_name'] = df['room_name'].apply(self._massage_room_name)

            # Sometime the same room may appear twice, and we want to keep the one with the largest capacity.
            df = df.drop_duplicates(subset='room_name', keep="last")
        finally:
            dbConnection.close()

        return df

    def read_meetings(self, area: int, meeting_date: date):
        dbConnection = self._sqlEngine().connect()
        try:
            # note: in the DB, end_time means the beginning of the next timeslot.
            #       E.g. if a room is booked from 5pm to 7pm, end_time = 7pm
            next_day = meeting_date + timedelta(days=1)
            df = pd.read_sql(_queries['mrbs_entry_join_room'] +
                             f'where r.area_id={area} and e.start_time >={_to_epoch(meeting_date)} and '
                             f'e.end_time < {_to_epoch(next_day)}', dbConnection)
        finally:
            dbConnection.close()

        df['room'] = df['room'].apply(self._massage_room_name)

        return df

    def read_facility_types(self):
        dbConnection = self._sqlEngine().connect()
        try:
            df = pd.read_sql(_queries['mrbs_facility_type'], dbConnection)
        finally:
            dbConnection.close()

        df['type'] = df['type'].apply(lambda x: x.strip())
        return df

    def read_facility(self, area=None):
        dbConnection = self._sqlEngine().connect()
        try:
            query = _queries['mrbs_facility_with_names']
            if area:
                query += f" where f.area_id={area}"

            df = pd.read_sql(query, dbConnection)
            df['room_name'] = df['room_name'].apply(self._massage_room_name)
        finally:
            dbConnection.close()

        return df

    def dump(self):
        folder = f"../dumps/{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        os.makedirs(folder, exist_ok=True)

        db = connect(self.host, self.user, self.password, self.database)
        cur = db.cursor()

        for table, query in _queries.items():
            if "_join_" in table:
                # Skip queries with join
                continue

            fn = os.path.join(folder, f'{table}.csv')
            cur.execute(query + ' order by id')

            print(f'[{datetime.now().strftime("%H:%M:%S")}] Dumping {table}')
            with open(fn, "w", newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([i[0] for i in cur.description])  # write headers
                csv_writer.writerows(cur)

        db.close()

    def insert_fac_data(self, area, data_file):
        df_rooms = self.read_rooms(area)
        df_truth_import = pd.read_csv(data_file)
        df = pd.merge(df_truth_import,
                      df_rooms.query(f'area_id=={area}')[['room_name', 'id']].rename({'id': 'room_id'}, axis=1),
                      left_on='地點', right_on='room_name')

        df_fac_types = self.read_facility_types()
        df2 = pd.merge(df, df_fac_types.query(f'area_id=={area}').rename({'id': 'facility_type_id'}, axis=1),
                       left_on='fac', right_on='type')
        df2 = df2[['room_id', 'area_id', 'facility_type_id']]

        df2.to_sql('mrbs_facility', self._sqlEngine(), index=False, if_exists='append')

    def insert_meetings(self, meetings_info, meeting_date: date):
        connection = connect(host=self.host, user=self.user, password=self.password, db=self.database, charset='utf8')
        try:
            with connection.cursor() as cursor:
                meeting_ids = []
                for info in meetings_info:
                    meeting = info['meeting']
                    meeting_times = meeting.meeting_times
                    start_time = Util.timeslot_to_dt(meeting_times[0], meeting_date)
                    # In the DB, end_time is the beginning of the timeslot after the meeting
                    end_time = Util.timeslot_to_dt(meeting_times[-1] + 1, meeting_date)

                    room = info['room']
                    if room.is_combined:
                        room_ids = room.id
                    else:
                        room_ids = [room.id]

                    for room_id in room_ids:
                        new_id = self._insert_meeting(cursor, meeting.name, start_time, end_time, room_id,
                                                      meeting.description)
                        meeting_ids.append(new_id)
        finally:
            connection.close()

        return meeting_ids

    def _insert_meeting(self, cursor, name, start_time: datetime, end_time: datetime, room_id, description=''):
        query = f'''
INSERT INTO mrbs_entry (start_time, end_time, entry_type, repeat_id, room_id, create_by, name, type, description)
VALUES ({_to_epoch(start_time)}, {_to_epoch(end_time)}, 0, 0, {room_id},
'administrator', convert(_latin1%s using utf8), 'I', convert(_latin1%s using utf8))'''
        logger.info(f'Adding meeting: start_time={start_time}, end_time={end_time}, room_id={room_id}, '
                    f'name={name}, description={description}')
        cursor.execute(query, (name, description))
        id = cursor.lastrowid
        logger.info(f'Meeting added, id={id}')

        return id


def _main():
    rmbs = Rmbs()
    Util.setup_logging()
    #rmbs.insert_fac_data(Rmbs.Area_Truth, 'data/truth_fac_import.csv')
    #df = rmbs.read_facility()
    #print(df)
    #rmbs.test()
    logger.info('done')


if __name__ == "__main__":
    _main()
