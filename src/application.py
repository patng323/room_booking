import pandas as pd
import xmltodict
from datetime import datetime, date
from os import path
import glob
import re
import logging
from church_calendar import earliest_booking_date

logger = logging.getLogger(__name__)

_applications_folder = path.join(path.dirname(path.abspath(__file__)), "../data/applications")


class Application:
    # These have to be in sync with the ENUM values in the DB
    STATUS_PENDING = "pending"
    STATUS_TOO_LATE = "too_late"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    @staticmethod
    def set_entries_status(application):
        for entry in application['entries']:
            allowed_earliest = earliest_booking_date(application['register_time'])
            if entry['event_date'] < allowed_earliest:
                entry['status'] = Application.STATUS_TOO_LATE
            else:
                entry['status'] = Application.STATUS_PENDING

    @staticmethod
    def get_applications(rmbs):
        print("TODO: The real one will download from an FTP server")

        # First read the meta file to know the timestamp of the last form we received in the last batch job
        last_timestamp = 0
        # if path.exists(_job_info_path):
        #     with open(_job_info_path, 'r') as f:
        #         job_info = json.load(f)
        #         last_timestamp = int(job_info.get(_key_last_timestamp, last_timestamp))

        filenames = glob.glob(_applications_folder + "/20*.xml")
        for fn in filenames:
            assert re.match(r'20\d{12}_\d+\.xml', path.basename(fn)), \
                "We assume the filename is in this format: 20210205163441_1302620215.xml"

        # Remove applications which we have handled already
        filenames = list(filter(lambda fn: int(path.basename(fn).split('_')[0]) > last_timestamp, filenames))

        applications = []
        for fn in filenames:
            with open(fn, 'r') as f:
                application = xmltodict.parse(f.read())['event']

            application['event_site'] = application.pop('eventSite')
            assert application['event_site'] in ['康澤', '真理樓', '教育樓']

            application['id'] = path.basename(fn)  # Use filename as the ID of the application

            # register_time == 交 Form 時間
            application['register_time'] = datetime.strptime(application.pop('registerDate'), '%Y%m%d%H%M%S')

            # Rename some fields; one reason is to match the column names in database
            application['size'] = int(application.pop('count'))
            application['phone_no'] = application.pop('phoneNo')
            application['in_charge'] = application.pop('incharge')
            application['unit_title'] = application.pop('unitTitle')

            application['entries'] = []

            for entry_no in range(1, 6):
                if not application[f'otherDate{entry_no}']:
                    continue

                entry = dict()
                entry['entry_no'] = entry_no
                entry['start_time'] = datetime.strptime(
                    application[f'otherDate{entry_no}'] + application[f'eventStartTime{entry_no}'],
                    '%Y-%m-%d%H:%M')
                entry['stop_time'] = datetime.strptime(
                    application[f'otherDate{entry_no}'] + application[f'eventStopTime{entry_no}'],
                    '%Y-%m-%d%H:%M')
                entry['event_date'] = date(year=entry['start_time'].year, month=entry['start_time'].month,
                                           day=entry['start_time'].day)

                application['entries'].append(entry)

            # Remove entry-related entries from the application dic
            for key in list(application.keys()):
                if key.startswith('otherDate') or key.startswith('get_week') or key.startswith('eventStartTime') or \
                        key.startswith('eventStopTime'):
                    application.pop(key)

            Application.set_entries_status(application)
            rmbs.insert_application(application)
            applications.append(application)

        # TODO:
        # (done) 1. Save each application and its entries to DB
        # (pending)1.b how to write a query to also get the no. of
        # (done) 2. For main.py, we need to provide a function to convert a list of application and their entries to a
        # dataframe
        # 3. When each application entry is processed, we need to set its status in DB
        # 4. After reading the application form from the file system, we need to move it to another folder
        # 5. We still need a status field for each application
        return applications

    @staticmethod
    def applications_to_df(applications):
        # Create a dataframe, with each row representing an entry in an application
        # Each row has the info about the entry as well as the parent application
        requests = []
        for app in applications:
            for entry in app['entries']:
                request = dict(app)  # Copy all the info about the parent applications
                request.pop('entries')  # Remove the list of entries
                request.update(entry)  # Then append the info from the entry
                requests.append(request)

        return pd.DataFrame(requests)

    @staticmethod
    def update_entries_status(df_entries, success, rmbs):
        for _, entry in df_entries.iterrows():
            rmbs.update_application_entry_status(entry['id'], entry['entry_no'],
                                                 Application.STATUS_SUCCESS if success else Application.STATUS_FAILED)

    @staticmethod
    def to_description(app):
        description = \
f'''{app['content']}
聚會單位名稱：{app['unit_title']}  所屬科/系：{app['unit2']}
備註：{app['note']}

申請人姓名：{app['in_charge']}
聯絡電話：{app['phone_no']}
所屬科/系：{app['unit1']} (單位：{app['supplement1']})
'''
        return description

    @staticmethod
    def to_event_name(app):
        event_name = ''
        if app['unit2']:
            event_name += f"{app['unit2']}："  # e.g. 青年科

        if app['unit_title']:
            part = f"{app['unit_title']}"  # e.g. 馬其頓團契
            if not event_name:
                part = part + '：'
            event_name += part

        if event_name:
            # if we have any info in the front
            event_name += f"（{app['subject']}）"
        else:
            event_name = app['subject']

        return event_name

