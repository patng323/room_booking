import xmltodict
from datetime import datetime, date
from os import path
import json
import glob
import re
import logging

logger = logging.getLogger(__name__)

_applications_folder = path.join(path.dirname(path.abspath(__file__)), "../data/applications")
_job_info_path = path.join(_applications_folder, '../job_info.json')
_key_last_timestamp = 'application.last_timestamp'


class Applications:

    @staticmethod
    def get_applications():
        print("TODO: The real one will download from an FTP server")

        # First read the meta file to know the timestamp of the last form we received in the last batch job
        last_timestamp = 0
        if path.exists(_job_info_path):
            with open(_job_info_path, 'r') as f:
                job_info = json.load(f)
                last_timestamp = int(job_info.get(_key_last_timestamp, last_timestamp))

        filenames = glob.glob(_applications_folder + "/20*.xml")
        for fn in filenames:
            assert re.match(r'20\d{12}_\d+\.xml', path.basename(fn)), \
                "We assume the filename is in this format: 20210205163441_1302620215.xml"

        # Remove applications which we have handled already
        filenames = list(filter(lambda fn: int(path.basename(fn).split('_')[0]) > last_timestamp, filenames))

        applications = []
        for fn in filenames:
            with open(fn, 'r') as f:
                form = xmltodict.parse(f.read())['event']

            assert form['eventSite'] in ['康澤', '真理樓', '教育樓']

            for entry in range(1, 6):
                if not form[f'otherDate{entry}']:
                    continue

                app = dict()
                app['application_file'] = path.basename(fn)
                app['registerTime'] = datetime.strptime(form['registerDate'], '%Y%m%d%H%M%S')
                app['startTime'] = datetime.strptime(form[f'otherDate{entry}'] + form[f'eventStartTime{entry}'],
                                                     '%Y-%m-%d%H:%M')
                app['stopTime'] = datetime.strptime(form[f'otherDate{entry}'] + form[f'eventStopTime{entry}'],
                                                    '%Y-%m-%d%H:%M')
                app['eventDate'] = date(year=app['startTime'].year, month=app['startTime'].month,
                                        day=app['startTime'].day)
                app['size'] = int(form['count'])

                event_name = ''
                if form['unit2']:
                    event_name += f"{form['unit2']}："  # e.g. 青年科

                if form['unitTitle']:
                    part = f"{form['unitTitle']}"  # e.g. 馬其頓團契
                    if not event_name:
                        part = part + '：'
                    event_name += part

                if event_name:
                    # if we have any info in the front
                    event_name += f"（{form['subject']}）"
                else:
                    event_name = form['subject']

                app['name'] = event_name

                app['eventSite'] = form['eventSite']
                app['description'] = \
f'''{form['content']}
聚會單位名稱：{form['unitTitle']}  所屬科/系：{form['unit2']}
備註：{form['note']}

申請人姓名：{form['incharge']}
聯絡電話：{form['phoneNo']}
所屬科/系：{form['unit1']} (單位：{form['supplement1']})
'''

                applications.append(app)

        return applications

    @staticmethod
    def update_job_info(applications):
        # Find the max date
        max_timestamp = 0
        for app in applications:
            fn = app['application_file']
            # File name is in this format: 20210217101702_971611315.xml
            timestamp = int(fn.split('_')[0])
            max_timestamp = max(max_timestamp, timestamp)

        if path.exists(_job_info_path):
            with open(_job_info_path, 'r') as f:
                job_info = json.load(f)
        else:
            job_info = {}

        job_info[_key_last_timestamp] = max_timestamp
        with open(_job_info_path, 'w') as f:
            json.dump(job_info, f)

        logging.info(f'Saved max timestamp {max_timestamp} to {_job_info_path}')





