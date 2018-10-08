# _*_ coding: utf-8 _*_

''' This module reads the metadata from a CKAN data package
and generates json that in turn can be fed to mkdcxml.py in
order to generate DatCite XML. This module depends very much on
the metadata and metadata-representation in CKAN, which is modified
by plugins and (in our case) very much in flux.

'''

import os
import ckanapi
import json
from collections import OrderedDict
from pprint import pprint
import re
from datetime import datetime

CKANHOST = 'https://eaw-ckan-dev1.eawag.wroot.emp-eaw.ch'
CKANAPIKEY = os.environ['CKAN_APIKEY']

class ExtractFromCKAN:

    def __init__(self, pkgname, doi):
        self.pkgname = pkgname
        self.ckanmeta = self.get_ckanmeta(pkgname)
        self.doi = doi
        self.output = {'resource': []}
        
    def get_ckanmeta(self, pkgname):
        with ckanapi.RemoteCKAN(CKANHOST, apikey=CKANAPIKEY) as conn:
            meta = conn.call_action('package_show', {'id': pkgname})
            return meta
        
    def _mkidentifier(self):
        self.output['resource'].append(
            {"identifier": {"val": self.doi, "att": {"identifierType": "DOI"}}}
        )
        
    def _creators(self):
        creators = {'creators': []}
        for a in self.ckanmeta['author']:
            last, rest = a.split(',')
            email = re.search('<(.+)>', rest)
            if email:
                email = email.groups()[0]
                rest = re.sub('<(.+)>', '', rest)
            last = last.strip()
            rest = rest.strip()
            orcid = input('Author: |{}, {}| email:|{}| : ORCID: '
                  .format(last, rest, email))
            eawag = input('Affiliation Eawag? [Y/n]')
            eawag = True if eawag in ['', 'Y', 'y', '1'] else False
            
            #print('{}, {}, <{}>, orcid:{}'.format(last, rest, email, orcid))
            creator = [
                {'creatorName': {'val': '{}, {}'.format(last, rest),
                                 "att": {"nameType": "Personal"}}},
 	        {'givenName': rest},
 	        {"familyName": last}
            ]
            if orcid:
                creator.append(
                    {'nameIdentifier': {'val': orcid,
                                        'att': {'nameIdentifierScheme': 'ORCID',
                                                'schemeURI': 'https://orcid.org/'}
                                        }})
            if eawag:
                creator.append(
                    {'affiliation': "Eawag: Swiss Federal Institute of Aquatic Science and Technology"}
                )
            creators['creators'].append({'creator': creator})
        self.output['resource'].append(creators)

    def _titles(self):
        title = self.ckanmeta['title'] 
        self.output['resource'].append(
            {"titles":
             [
	         {"title": {"val": title, "att": {"lang": "en"}}}
             ]}
        )
        
    def _publisher(self):
        self.output['resource'].append(
            {"publisher": "Eawag: Swiss Federal Institute of Aquatic Science and Technology"}
        )
        
    def _publication_year(self):
        # We assume publication happened in the same year as metadata was created.
        pubyear = datetime.strptime(
            self.ckanmeta['metadata_created'], '%Y-%m-%dT%H:%M:%S.%f').year
        self.output['resource'].append(
            {'publicationYear': pubyear}
        )
        
    def _resource_type(self):
        restype = input('ResourceType [Publication Data Package]: ')
        restype = 'Publication Data Package' if restype == '' else restype
        restype_general = input('ResourceTypeGeneral [Collection]'
                                '(Audiovisual, Dataset, Image, Model, Software,'
                                'Sound, Text, Other) ')
        restype_general = 'Collection' if restype_general == '' else restype_general
        if not restype_general in ['Audiovisual', 'Collection', 'Dataset',
                                   'Image', 'Model', 'Software', 'Sound',
                                   'Text', 'Other']:
            raise Exception('Illegal ResourceTypeGeneral')
        self.output['resource'].append(
            {'resourceType': {'val': restype,
                              'att': {'resourceTypeGeneral': restype_general}}
            })
        
    def _subjects(self):
        generic = self.ckanmeta.get('generic-terms') or []
        print(generic)
        taxa = self.ckanmeta.get('taxa') or []
        substances = self.ckanmeta.get('substances') or []
        systems = self.ckanmeta.get('systems') or []
        tags = [t['display_name'] for t in self.ckanmeta.get('tags')]
        keywords = generic + taxa + substances + systems + tags
        keywords = [k for k in keywords if k not in ['none']]
        subjects = [
            {"subject": {"val": k, "att": {"lang": "en"}}} for k in keywords]
        self.output['resource'].append({'subjects': subjects})

    def _converttime(self, solrtimerange):
        if re.search('\s+TO\s+', solrtimerange):
            fro, to = solrtimerange.split('TO')
            fro = fro.strip()
            fro = '' if fro == '*' else fro
            to = to.strip()
            to = '' if to == '*' else to
            return '{}/{}'.format(fro, to)
        else:
            solrtimerange = '/' if solrtimerange.strip() == '*' else  solrtimerange.strip()
            return solrtimerange
    
        
    def _dates(self):
        # We interpret CKAN's 'metadata_modified' as 'Submitted',
        # assuming that the last changes where made shortly before
        # DOI creation was requested.
        submitted = datetime.strptime(
            self.ckanmeta['metadata_modified'], '%Y-%m-%dT%H:%M:%S.%f')
        submitted = [
            {"date": {"val": submitted.strftime('%Y-%m-%d'),
                      "att": {"dateType": "Submitted"}}}]
        collected = [{"date": {"val": self._converttime(t),
                               "att": {"dateType": "Collected"}}}
                     for t in self.ckanmeta['timerange']]
         
        self.output['resource'].append(
            {'dates': submitted + collected}
        )

    def _languages(self):
         self.output['resource'].append({'language': 'en'})

    def _version(self):
        version = input('Version [1.0]: ')
        version = '1.0' if version == '' else version
        self.output['resource'].append({'version': version})

    def _rightslist(self):
        self.output['resource'].append(
            {'rightsList':
             [
	         {'rights': {'val': 'CC0 1.0 Universal (CC0 1.0) '
                             'Public Domain Dedication',
                             'att': {'rightsURI':
                                     'https://creativecommons.org/publicdomain'
                                     '/zero/1.0/',
                                     'lang': 'en'}}}
             ]
            })

    def _descriptions(self):



             {"descriptions":
      [
	  {"description":
	   {"val": "Anonymized data and R code needed to replicate the analysis presented in the study \"Networks of Swiss water governance issues. Studying fit between media attention and organizational activity\" to be published in Society & Natural Resources.\r\nThe study looks at how relations between Swiss water governance issues are portrayed in the media as compared to the way organizations involved in water governance reflect these relations in their activity.\r\nThis is a paper output of the SNF funded project \"Overlapping subsystems\". Access to the complete, non-anonymized dataset is restricted.\r\nStudy doi: tbd",
	    "att": {"descriptionType": "Abstract"}
	   }
	  }
      ]
        

def test_get_ckanmeta():
    C = ExtractFromCKAN('ecolihandwashingwaterandhandsinharare', '10.25678/000088')
    # C._mkidentifier()
    # pprint(C.output)
    # C._creators()
    # pprint(C.output)
    # C._titles()
    # pprint(C.output)
    # C._publisher()
    # C._publication_year()
    # pprint(C.output)
    # C._resource_type()
    # pprint(C.output)
    # C._subjects()
    # pprint(C.output)
    C._dates()
    C._languages()
    C._version()
    C._rightslist()
    pprint(C.output)
        
test_get_ckanmeta()

