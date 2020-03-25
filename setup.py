# _*_ coding: utf-8 _*_

from setuptools import setup, find_packages
setup(
    name = 'mkdcxml',
    version = '0.1',
    packages = find_packages(),
    install_requires = ['lxml>=4.1.1',
                        'docopt>=0.6.2'],
    author = 'Harald von Waldow',
    author_email = 'harald.vonwaldow@eawag.ch',
    description = ("Returns the XML representation of the DataCite metadata"
                   " schema (https://schema.datacite.org/meta/kernel-4.1/)."
                   " Input is a json file in an special format."),
    license = " GNU AFFERO GENERAL PUBLIC LICENSE",
    keywords = 'DataCite metadata XML',
    entry_points = {
        'console_scripts':
        ['mkdcxml=mkdcxml.mkdcxml:main']
    }
)
