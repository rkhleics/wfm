from setuptools import setup


with open('README.rst') as readme_file:
    README = readme_file.read()

setup(
    name='wfm',
    description=(
        'A command-line interface for adding to your WorkflowMax timesheet.'
    ),
    url='https://github.com/rkhleics/wfm',
    author='colons',
    author_email='pypi@colons.co',
    version='0.1.3',
    license="BSD",
    platforms=['any'],
    packages=['wfm'],
    scripts=['scripts/wfm'],
    install_requires=[
        'ansicolors',
        'pyyaml',
        'requests',
        'six',
    ],
    long_description=README,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
    ],
)
