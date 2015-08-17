from __future__ import print_function, unicode_literals

import colors
from lxml import etree
import requests
from six.moves import input


def input_valid(message, validate):
    result = None
    while result is None:
        try:
            return validate(input(message))
        except Exception as e:
            print(e)
            print('try again')


class WFMError(Exception):
    pass


class Client(object):
    base = 'https://api.workflowmax.com/{}'
    email = '[redacted]'

    def request(self, method, path, **extra_params):
        params = {
            'apiKey': '[redacted]',
            'accountKey': '[redacted]',
        }
        params.update(extra_params)
        resp = requests.request(method, self.base.format(path), params=params)
        if resp.status_code != 200:
            raise ValueError('non-200 response: {}'.format(resp.status_code))
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

    def get_my_id(self):
        for staff in self.request('get', 'staff.api/list').find('StaffList'):
            if staff.find('Email').text == self.email:
                return staff.find('ID').text

        raise ValueError('could not find staff member with email address {}'
                         .format(self.email))

    def get_my_jobs(self):
        my_id = client.get_my_id()
        return [
            job for job in self.request('get', 'job.api/current').find('Jobs')
            if my_id in [s.find('ID').text for s in job.find('Assigned')]
        ]

    def get_tasks_for_job(self, job_id):
        return client.request(
            'get', 'job.api/get/{}'.format(job_id)
        ).find('Job').find('Tasks')


if __name__ == '__main__':
    client = Client()
    jobs = client.get_my_jobs()

    for i, job in enumerate(jobs):
        print('{index}: {client} | {job}'.format(
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
