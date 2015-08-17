from __future__ import print_function, unicode_literals, division

from collections import defaultdict
import datetime
import os
from sys import exit
import xml.etree.ElementTree as etree

import colors
from dateutil.parser import parse as parse_date
import requests
from six.moves import input
import yaml


DAY_BUFFER = 14
WFM_DATE_FORMAT = '%Y%m%d'
SHORT_DATE = '%a %b %d'

CONFIG_TUTORIAL = """
The config is a YAML file with values for 'email', 'apiKey', and 'accountKey'.

For example, it might look like this:

email: me@company.tld
apiKey: 00000000000000000000000000000000
accountKey: 00000000000000000000000000000000

If you don't have API keys, you'll need to contact WorkflowMax for them; you
can do that at http://www.workflowmax.com/contact-us
""".strip()


def get_config_yaml():
    path = os.path.join(os.environ.get('HOME'), '.wfm.yml')
    if not os.path.isfile(path):
        print ('Please make a config file at {}\n\n{}'.format(
            path, CONFIG_TUTORIAL))
        exit(1)
    with open(path) as yf:
        return yaml.load(yf)


config_yaml = get_config_yaml()
EMAIL = config_yaml['email']
API_KEY = config_yaml['apiKey']
ACCOUNT_KEY = config_yaml['accountKey']


def input_valid(message, validate):
    result = None
    while result is None:
        try:
            return validate(input(message))
        except Exception as e:
            print(e)
            print('try again')


def strfdate(date):
    return date.strftime(WFM_DATE_FORMAT)


def strfmins(minutes):
    hours = minutes // 60
    remainder = minutes % 60
    return '{}:{:02}'.format(hours, remainder)


def strpmins(user_string):
    if ':' not in user_string:
        user_string = '0:{}'.format(user_string)

    hours, minutes = (int(i) for i in user_string.split(':', 1))
    return minutes + hours * 60


class WFMError(Exception):
    pass


class Client(object):
    base = 'https://api.workflowmax.com/{}'
    email = EMAIL

    def __init__(self):
        self.my_id = self._get_my_id()

    def request(self, method, path, data=None, **extra_params):
        params = {
            'apiKey': API_KEY,
            'accountKey': ACCOUNT_KEY,
        }
        params.update(extra_params)
        resp = requests.request(
            method, self.base.format(path), params=params, data=data,
        )

        if resp.status_code != 200:
            raise WFMError('{}\n\nnon-200 response: {}'.format(
                resp.status_code, resp.content))

        try:
            parsed = etree.fromstring(resp.content)
        except etree.XMLSyntaxError:
            print(resp.content)
            raise

        if parsed.find('Status').text != 'OK':
            raise WFMError('{}: {}'.format(
                parsed.find('Status').text,
                etree.tostring(parsed),
            ))

        return parsed

    def _get_my_id(self):
        for staff in self.request('get', 'staff.api/list').find('StaffList'):
            if staff.find('Email').text == self.email:
                return staff.find('ID').text

        raise ValueError('could not find staff member with email address {}'
                         .format(self.email))

    def get_my_jobs(self):
        return [
            job for job in self.request('get', 'job.api/current').find('Jobs')
            if self.my_id in [s.find('ID').text for s in job.find('Assigned')]
        ]

    def get_tasks_for_job(self, job_id):
        return client.request(
            'get', 'job.api/get/{}'.format(job_id)
        ).find('Job').find('Tasks')

    def get_my_recent_times(self):
        return [
            t for t in client.request('get', 'time.api/list', **{
                'from': strfdate(datetime.date.today() -
                                 datetime.timedelta(days=DAY_BUFFER)),
                'to': strfdate(datetime.date.today() +
                               datetime.timedelta(days=1)),
            }).find('Times')
            if t.find('Staff').find('ID').text == self.my_id
        ]


client = Client()


def get_date():
    times = client.get_my_recent_times()
    today = datetime.date.today()
    calendar = []
    entries_by_date_text = defaultdict(list)

    for time in times:
        entries_by_date_text[time.find('Date').text].append(time)

    entries_by_date = {
        parse_date(k).date(): v for k, v in entries_by_date_text.items()
    }

    dates = {
        d: sum([int(time.find('Minutes').text) for time in ts])
        for d, ts in entries_by_date.items()
    }

    for days_ago in range(DAY_BUFFER, -1, -1):
        target_date = today - datetime.timedelta(days=days_ago)
        calendar.append((target_date, dates.get(target_date, 0)))

    print()

    for i, (date, minutes) in enumerate(calendar):
        weekday = date.weekday() not in (5, 6)
        bold_if_weekday = colors.bold if weekday else lambda s: s
        minute_coloration = colors.green if minutes else colors.red
        print('{index}: {time} {weekday} {date}'.format(
            index=colors.bold('{:3}'.format(i+1)),
            weekday='-' if weekday else ' ',
            date=bold_if_weekday(colors.yellow(date.strftime(SHORT_DATE))),
            time=bold_if_weekday(minute_coloration(strfmins(minutes))),
        ))

    date = input_valid(
        '\npick a day (1-{}, today if blank): '.format(len(calendar)),
        lambda i: calendar[(int(i) if i else len(calendar))-1][0],
    )

    existing_entries = entries_by_date.get(date)

    if existing_entries:
        print('\n times already entered for {}:'.format(
            date.strftime(SHORT_DATE),
        ))
        for entry in existing_entries:
            note = entry.find('Note').text
            note_format = colors.cyan if note else colors.red
            print(' {time} - {note}'.format(
                time=colors.bold(strfmins(int(entry.find('Minutes').text))),
                note=note_format(note or '[no description]'),
            ))

    return date


def get_job():
    jobs = sorted(
        client.get_my_jobs(),
        key=lambda j: (
            j.find('Client').find('Name').text.strip(),
            j.find('Name').text.strip(),
        )
    )

    print()

    for i, job in enumerate(jobs):
        print('{index}: {job} | {client}'.format(
            index=colors.bold('{:3}'.format(i+1)),
            client=colors.blue(job.find('Client').find('Name').text.strip()),
            job=colors.magenta(job.find('Name').text.strip()),
        ))

    return input_valid(
        '\npick a job (1-{}): '.format(len(jobs)),
        lambda i: jobs[int(i)-1],
    )


def get_task(job):
    tasks = sorted(
        client.get_tasks_for_job(job.find('ID').text),
        key=lambda t: t.find('Name').text.strip(),
    )
    if len(tasks) == 0:
        print('there are no tasks on that job, sorry :<')
        exit(1)
    elif len(tasks) == 1:
        task, = tasks
        return task
    else:
        print()
        for i, task in enumerate(tasks):
            print('{index}: {task}'.format(
                index=colors.bold('{:3}'.format(i+1)),
                task=colors.green(task.find('Name').text.strip()),
            ))

        return input_valid(
            '\npick a task (1-{}): '.format(len(tasks)),
            lambda i: tasks[int(i)-1],
        )


def get_description():
    description_lines = []

    print('\nwhat were you up to? (end input by hitting return twice):\n')

    while True:
        line = input()
        if not line:
            break
        description_lines.append(line)

    return '\r\n'.join(description_lines)


def submit_time(job, task, date, minutes, description):
    print("submitting...")

    entry = etree.Element('Timesheet')
    for name, value in [
        ('Job', job.find('ID').text),
        ('Task', task.find('ID').text),
        ('Staff', client.my_id),
        ('Date', strfdate(date)),
        ('Minutes', '{}'.format(minutes)),
        ('Note', description),
    ]:
        sub = etree.SubElement(entry, name)
        sub.text = value

    client.request('post', 'time.api/add', data=etree.tostring(entry))

    print("okay, that's submitted")
