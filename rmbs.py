#!/Users/patrickng/anaconda3/envs/py36/bin/python
import yaml
from sqlalchemy import create_engine
from pymysql import connect
from datetime import datetime
import os
import csv
import pandas as pd

_queries = {
    "mrbs_area": '''
SELECT id, CONVERT(BINARY CONVERT(area_name USING latin1) USING utf8) as area_name, area_admin_email
FROM mrbs.mrbs_area order by id;''',

    "mrbs_entry": '''
select 
id,start_time,end_time,entry_type,repeat_id,room_id,timestamp,create_by,
CONVERT(BINARY CONVERT(name USING latin1) USING utf8) as name,
type,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description
from mrbs_entry
order by id;''',

    "mrbs_room": '''
SELECT 
id,area_id,room_zone,room_group,
CONVERT(BINARY CONVERT(room_name USING latin1) USING utf8) as room_name,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description,
CONVERT(BINARY CONVERT(equipment USING latin1) USING utf8) as equipment,
capacity,room_admin_email
FROM mrbs.mrbs_room order by id;''',
    
    "mrbs_repeat": '''
SELECT
id,start_time,end_time,rep_type,end_date,rep_opt,room_id,timestamp,create_by,
CONVERT(BINARY CONVERT(name USING latin1) USING utf8) as name,
type,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description,
rep_num_weeks,rep_spec_week,rep_date
FROM mrbs.mrbs_repeat order by id;'''
}

class Rmbs:
    def __init__(self):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            self.host = config['host']
            self.user = config['user']
            self.password = config['password']
            self.database = config['database']

    def test(self):
        connection = connect(host=self.host, user=self.user, password=self.password, db=self.database, charset='utf8')
        with connection.cursor() as cursor:
            start_time = datetime.strptime("2020-12-13 10:00:00", "%Y-%m-%d %H:%M:%S").strftime("%s")
            end_time = datetime.strptime("2020-12-13 10:30:00", "%Y-%m-%d %H:%M:%S").strftime("%s")
            name = "大食會's 時間！"
            description = "係咁食\n之後就太飽了."
            # Create a new record
            query = f'''
INSERT INTO mrbs_entry (start_time, end_time, entry_type, repeat_id, room_id, create_by, name, type, description)
VALUES ({start_time}, {end_time}, 0, 0, 202,
'administrator', convert(_latin1%s using utf8), 'I', convert(_latin1%s using utf8))'''
            cursor.execute(query, (name, description))

        connection.commit()

    def read_area(self):
        sqlEngine = create_engine(f'mysql+pymysql://{self.user}:{self.password}@{self.host}/{self.database}',
                                  pool_recycle=3600)
        dbConnection = sqlEngine.connect()
        frame = pd.read_sql(_queries['mrbs_area'], dbConnection)
        pd.set_option('display.expand_frame_repr', False)
        print(frame)
        dbConnection.close()

    def dump(self):
        folder = f"dumps/{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        os.makedirs(folder, exist_ok=True)

        db = connect(self.host, self.user, self.password, self.database)
        cur = db.cursor()

        for table, query in _queries.items():
            fn = os.path.join(folder, f'{table}.csv')
            cur.execute(query)

            print(f'[{datetime.now().strftime("%H:%M:%S")}] Dumping {table}')
            with open(fn, "w", newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([i[0] for i in cur.description])  # write headers
                csv_writer.writerows(cur)

        db.close()


if __name__ == "__main__":
    rmbs = Rmbs()
    rmbs.test()
