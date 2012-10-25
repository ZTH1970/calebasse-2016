#!/usr/bin/python
from setuptools import setup, find_packages
import os

setup(name='calebasse',
        version='0.1',
        license='AGPLv3',
        description='',
        url='http://dev.entrouvert.org/projects/calebasse/',
        download_url='http://repos.entrouvert.org/calebasse.git/',
        author="Entr'ouvert",
        author_email="info@entrouvert.com",
        packages=find_packages(os.path.dirname(__file__) or '.'),
        install_requires=[
            'django >= 1.4',
            'south >= 0.7',
            'django-reversion >= 1.6.2',
            'python-dateutil >=1.5, < 2.0',
            'django-model-utils < 1.2.0',
            'django-ajax-selects < 1.3.0',
            'django-widget-tweaks < 1.2.0',
            'django-tastypie>=0.9, < 1.0',
            'interval == 1.0.0',
        ],
        dependency_links = [
            'http://django-swingtime.googlecode.com/files/django-swingtime-0.2.1.tar.gz#egg=django-swingtime-0.2.1',
        ],
)
