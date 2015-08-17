from __future__ import print_function, unicode_literals, division

import datetime
import os
from sys import exit

import colors
from dateutil.parser import parse as parse_date
from lxml import etree
import requests
from six.moves import input
import yaml


DAY_BUFFER = 14
DATE_FORMAT = '%Y%m%d'

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
    return date.strftime(DATE_FORMAT)


def strfmins(minutes):
    hours = minutes // 60
    remainder = minutes % 60
    return '{}:{:02}'.format(hours, remainder)


class WFMError(Exception):
    pass


class Client(object):
    base = 'https://api.workflowmax.com/{}'
    email = EMAIL

    def __init__(self):
        self.my_id = self._get_my_id()

    def request(self, method, path, **extra_params):
        params = {
            'apiKey': API_KEY,
            'accountKey': ACCOUNT_KEY,
        }
        params.update(extra_params)
        resp = requests.request(method, self.base.format(path), params=params)

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


if __name__ == '__main__':
    client = Client()

    jobs = sorted(
        client.get_my_jobs(),
        key=lambda j: (
            j.find('Client').find('Name').text.strip(),
            j.find('Name').text.strip(),
        )
    )

    for i, job in enumerate(jobs):
        print('{index}: {job} | {client}'.format(
            index=colors.bold('{:3}'.format(i+1)),
            client=colors.cyan(job.find('Client').find('Name').text.strip()),
            job=colors.magenta(job.find('Name').text.strip()),
        ))

    job = input_valid(
        '\npick a job (1-{}): '.format(len(jobs)),
        lambda i: jobs[int(i)-1],
    )

    tasks = client.get_tasks_for_job(job.find('ID').text)
    if len(tasks) == 0:
        print('there are no tasks on that job, sorry :<')
    elif len(tasks) == 1:
        task, = tasks
    else:
        for i, task in enumerate(tasks):
            print('{index}: {task}'.format(
                index=colors.bold('{:3}'.format(i+1)),
                task=colors.green(task.find('Name').text.strip()),
            ))

        task = input_valid(
            '\npick a task (1-{}): '.format(len(tasks)),
            lambda i: tasks[int(i)-1],
        )

    times = client.get_my_recent_times()
    today = datetime.date.today()
    calendar = []
    for days_ago in range(DAY_BUFFER, -1, -1):
        target_date = today - datetime.timedelta(days=days_ago)
        total_minutes = 0
        for time in times:
            if parse_date(time.find('Date').text).date() == target_date:
                total_minutes += int(time.find('Minutes').text)
        calendar.append((target_date, total_minutes))

    print()

    for i, (date, minutes) in enumerate(calendar):
        weekday = date.weekday() not in (5, 6)
        bold_if_weekday = colors.bold if weekday else lambda s: s
        minute_coloration = colors.green if minutes else colors.red
        print('{index}: {time} {weekday} {date}'.format(
            index=colors.bold('{:3}'.format(i+1)),
            weekday='-' if weekday else ' ',
            date=colors.yellow(date.strftime('%a %b %d')),
            time=bold_if_weekday(minute_coloration(strfmins(minutes))),
        ))

    date = input_valid(
        '\npick a day (1-{0}, default {0}): '.format(len(calendar)),
        lambda i: calendar[(int(i) if i else len(calendar))-1][1],
    )
