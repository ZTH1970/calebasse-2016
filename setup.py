#!/usr/bin/python
from setuptools import setup, find_packages
import os

def get_version():
    from alcide import __version__
    version = __version__
    if os.path.exists('.git'):
        import subprocess
        p = subprocess.Popen(['git','describe','--dirty','--match=v*'],
                stdout=subprocess.PIPE)
        result = p.communicate()[0]
        assert p.returncode == 0, 'git returned non-zero'
        new_version = result.split()[0][1:]
        assert new_version.split('-')[0] == version, '__version__ must match the last git annotated tag'
        version = new_version.replace('-', '.')
    return version


setup(name='alcide',
        version=get_version(),
        license='AGPLv3',
        description='',
        url='http://dev.entrouvert.org/projects/alcide/',
        download_url='http://repos.entrouvert.org/alcide.git/',
        author="Paradis Charlotte &",
        author_email="info@entrouvert.com",
        packages=find_packages(os.path.dirname(__file__) or '.'),
        install_requires=[
            'Django >= 1.5, < 1.6',
            'south >= 0.8.4',
            'django-reversion == 1.6.6',
            'python-dateutil >= 2.2, < 2.3',
            'django-model-utils >= 1.5.0',
            'django-ajax-selects < 1.3.0',
            'django-widget-tweaks < 1.2.0',
            'django-tastypie == 0.9.14',
            'django-select2 < 4.3',
            'interval == 1.0.0',
            'python-entrouvert >= 1.3',
            'django-localflavor',
            'xhtml2pdf',
            'M2Crypto',
            'django_journal',
        ],
        dependency_links = [
            'http://django-swingtime.googlecode.com/files/django-swingtime-0.2.1.tar.gz#egg=django-swingtime-0.2.1',
        ],
)
