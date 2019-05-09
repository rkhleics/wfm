from __future__ import print_function, unicode_literals, division

import datetime
import os
from sys import exit, stdin
import xml.etree.ElementTree as etree

import colors
import requests
from six import moves, PY2
import yaml


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
        return yaml.load(yf, Loader=yaml.SafeLoader)


config_yaml = get_config_yaml()
EMAIL = config_yaml['email']
API_KEY = config_yaml['apiKey']
ACCOUNT_KEY = config_yaml['accountKey']


def decoded_input(*args):
    result = moves.input(*args)

    if PY2:
        return result.decode(stdin.encoding)
    else:
        return result


def input_valid(message, validate):
    result = None
    while result is None:
        try:
            return validate(decoded_input(message))
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

    def get_my_times_for_date(self, date):
        return [
            t for t in client.request('get', 'time.api/list', **{
                'from': strfdate(date),
                'to': strfdate(date),
            }).find('Times')
            if t.find('Staff').find('ID').text == self.my_id
        ]


client = Client()


def get_date():
    today = datetime.date.today()
    times = client.get_my_times_for_date(today)
    total_minutes = 0

    if times:
        print('\n  already entered for {}:'.format(
            today.strftime(SHORT_DATE),
        ))
        for entry in times:
            note = entry.find('Note').text
            note_format = colors.cyan if note else colors.red
            minutes = int(entry.find('Minutes').text)
            total_minutes += minutes
            print('  {time} - {note}'.format(
                time=colors.bold(strfmins(minutes)),
                note=note_format(note or '[no description]'),
            ))

        print ('\n  {time} - total'.format(
            time=colors.bold(strfmins(total_minutes)),
        ))

    return today


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
            index=colors.bold('{:3}'.format(i + 1)),
            client=colors.blue(job.find('Client').find('Name').text.strip()),
            job=colors.magenta(job.find('Name').text.strip()),
        ))

    return input_valid(
        '\npick a job (1-{}): '.format(len(jobs)),
        lambda i: jobs[int(i) - 1],
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
                index=colors.bold('{:3}'.format(i + 1)),
                task=colors.green(task.find('Name').text.strip()),
            ))

        return input_valid(
            '\npick a task (1-{}): '.format(len(tasks)),
            lambda i: tasks[int(i) - 1],
        )


def get_description():
    description_lines = []

    print('\nwhat were you up to? (end input by submitting an empty line):\n')

    while True:
        line = decoded_input()
        if not line:
            break
        description_lines.append(line)

    return u'\r\n'.join(description_lines)


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
