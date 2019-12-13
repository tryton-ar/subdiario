#!/usr/bin/env python
# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from setuptools import setup
import re
import os
import io
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
name = 'trytonar_subdiario'

download_url = 'https://github.com/tryton-ar/subdiario/tree/%s.%s' % (
    major_version, minor_version)

requires = []
for dep in info.get('depends', []):
    if dep == 'account_invoice_ar':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif dep == 'party_ar':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif dep == 'citi_afip':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif not re.match(r'(ir|res)(\W|$)', dep):
        requires.append(get_require_version('trytond_%s' % dep))
requires.append(get_require_version('trytond'))
requires.append('httplib2')
requires.append('pyafipws')
requires.append('pysimplesoap')
requires.append('unidecode >= 1.0.23')

tests_require = [get_require_version('proteus')]
dependency_links = [
    'https://github.com/tryton-ar/account_invoice_ar/tarball/%s.%s#egg=trytonar_account_invoice_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/party_ar/tarball/%s.%s#egg=trytonar_party_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/citi_afip/tarball/%s.%s#egg=trytonar_citi_afip-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/account_ar/tarball/%s.%s#egg=trytonar_account_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/bank_ar/tarball/%s.%s#egg=trytonar_bank_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/reingart/pyafipws/tarball/py3k#egg=pyafipws',
    'https://github.com/pysimplesoap/pysimplesoap/tarball/stable_py3k#egg=pysimplesoap',
    ]

setup(name=name,
    version=version,
    description='Tryton module that add reports IVA Ventas/Compras',
    long_description=read('README'),
    author='tryton-ar',
    url='https://github.com/tryton-ar/subdiario',
    download_url=download_url,
    package_dir={'trytond.modules.subdiario': '.'},
    packages=[
        'trytond.modules.subdiario',
        'trytond.modules.subdiario.tests',
        ],
    package_data={
        'trytond.modules.subdiario': (info.get('xml', [])
            + ['tryton.cfg', 'view/*.xml', 'locale/*.po', '*.fods']),
        },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Financial :: Accounting',
        ],
    license='GPL-3',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    subdiario = trytond.modules.subdiario
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    use_2to3=True,
    )
