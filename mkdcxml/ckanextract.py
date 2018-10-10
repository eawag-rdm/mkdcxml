# _*_ coding: utf-8 _*_

# This module requires Python >= 3.5
# © 2018, Harald von Waldow @ Eawag

# This program is licensed under the
# GNU AFFERO GENERAL PUBLIC LICENSE version 3
# https://www.gnu.org/licenses/agpl.txt


'''ckanextract

Usage:
  ckanextract <doi> <package_name> <outputfile>
  ckanextract -h

Options:
  --help, -h  Show this screen

Arguments:
  <doi>          DOI in the form "10.25678/000011"
  <package_name> The CKAN package name
  <outputfile>   The file to which the intermediate json is written

This module reads the metadata from a CKAN data package
and generates json that in turn can be fed to mkdcxml.py in
order to generate DatCite XML. This module depends very much on
the metadata and metadata-representation in CKAN, which is modified
by plugins and (in our case) very much in flux.

Currently this module covers a subset of the
DataCite Metadata Schema 4.1 (https://schema.datacite.org/meta/kernel-4.1)

'''

import os
import ckanapi
import json
import re
import sys
from pprint import pprint
from datetime import datetime
from docopt import docopt

CKANHOST = 'https://eaw-ckan-dev1.eawag.wroot.emp-eaw.ch'
CKANAPIKEY = os.environ['CKAN_APIKEY']
PUBLISHER = 'Eawag: Swiss Federal Institute of Aquatic Science and Technology'
DEFAULT_AFFILIATION = 'Eawag: Swiss Federal Institute of Aquatic Science and Technology'

class CKANExtract:

    @staticmethod
    def elements():
        return [
            (1, 'identifier'),
            (2, 'creators'),
            (3, 'titles'),
            (4, 'publisher'),
            (5, 'publicationYear'),
            (6, 'resourceType'),
            (7, 'subjects'),
            (8, 'contributors'),
            (9, 'dates'),
            (10, 'language'),
            (11, 'alternateIdentifiers'),
            (12, 'relatedIdentifiers'),
            (13, 'sizes'),
            (14, 'formats'),
            (15, 'version'),
            (16, 'rightslist'),
            (17, 'descriptions'),
            (18, 'geolocations'),
            (19, 'fundingReferences'),
        ]

        
    def __init__(self, pkgname, doi, outfile):
        self.pkgname = pkgname
        self.ckanmeta = self.get_ckanmeta(pkgname)
        self.doi = doi
        self.output = {'resource': []}
        self.outfile = outfile
        
    def get_ckanmeta(self, pkgname):
        with ckanapi.RemoteCKAN(CKANHOST, apikey=CKANAPIKEY) as conn:
            meta = conn.call_action('package_show', {'id': pkgname})
            return meta

    def _date_from_iso(self, isodate):
        return datetime.strptime(isodate, '%Y-%m-%dT%H:%M:%S.%f')

    def _converttime(self, solrtimerange):
        # Converts SOLR date & daterange - format to RKMS-ISO8601
        if re.search('\s+TO\s+', solrtimerange):
            fro, to = solrtimerange.split('TO')
            fro = fro.strip()
            fro = '' if fro == '*' else fro
            to = to.strip()
            to = '' if to == '*' else to
            return '{}/{}'.format(fro, to)
        else:
            isotimerange = '/' if solrtimerange.strip() == '*' else  solrtimerange.strip()
            return isotimerange

        
    def xs_identifier(self):
        self.output['resource'].append(
            {"identifier": {"val": self.doi, "att": {"identifierType": "DOI"}}}
        )
        
    def xs_creators(self):
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
                    {'affiliation': DEFAULT_AFFILIATION}
                )
            creators['creators'].append({'creator': creator})
        self.output['resource'].append(creators)

    def xs_titles(self):
        title = self.ckanmeta['title'] 
        self.output['resource'].append(
            {"titles":
             [
	         {"title": {"val": title, "att": {"lang": "en"}}}
             ]}
        )
        
    def xs_publisher(self):
        self.output['resource'].append(
            {"publisher": PUBLISHER}
        )
        
    def xs_publicationYear(self):
        # We assume publication happened in the same year as metadata was created.
        pubyear = self._date_from_iso(self.ckanmeta['metadata_created']).year
        self.output['resource'].append(
            {'publicationYear': str(pubyear)}
        )
        
    def xs_resourceType(self):
        restype = input('ResourceType [Publication Data Package]: ')
        restype = 'Publication Data Package' if restype == '' else restype
        restype_general = False
        while not restype_general:
            restype_general = input('ResourceTypeGeneral [Collection]'
                                    '(Audiovisual, Dataset, Image, Model,'
                                    ' Software, Sound, Text, Other) : ')
            restype_general = 'Collection' if restype_general == '' else restype_general
            if not restype_general in ['Audiovisual', 'Collection', 'Dataset',
                                       'Image', 'Model', 'Software', 'Sound',
                                       'Text', 'Other']:
                print('Illegal ResourceTypeGeneral [{}]\n'.format(restype_general))
                restype_general = False
        self.output['resource'].append(
            {'resourceType': {'val': restype,
                              'att': {'resourceTypeGeneral': restype_general}}
            })
        
    def xs_subjects(self):
        # This has to be amended if subjects (keywords) are from
        # a specific ontology. It also needs to change if
        # CKAN metadata schema changes in any of the fields suitable
        # as keywords
        generic = self.ckanmeta.get('generic-terms') or []
        taxa = self.ckanmeta.get('taxa') or []
        substances = self.ckanmeta.get('substances') or []
        systems = self.ckanmeta.get('systems') or []
        tags = [t['display_name'] for t in self.ckanmeta.get('tags')]
        keywords = generic + taxa + substances + systems + tags
        keywords = [k for k in keywords if k not in ['none']]
        subjects = [
            {"subject": {"val": k, "att": {"lang": "en"}}} for k in keywords]
        self.output['resource'].append({'subjects': subjects})
        
    def xs_contributors(self):
        # Not implemented
        return
        
    def xs_dates(self):
        # We interpret CKAN's 'metadata_modified' as 'Submitted',
        # assuming that the last changes where made shortly before
        # DOI creation was requested.
        # The only other date(s) considered here are dateType=Collected
        # Other dateTyps (https://schema.datacite.org/meta/kernel-4.1
        # /include/datacite-dateType-v4.1.xsd) would have to be added.

        # Also: Everything is UTC everywhere.
        submitted = self._date_from_iso(self.ckanmeta['metadata_modified'])
        submitted = [
            {"date": {"val": submitted.strftime('%Y-%m-%d'),
                      "att": {"dateType": "Submitted"}}}]
        collected = [{"date": {"val": self._converttime(t),
                               "att": {"dateType": "Collected"}}}
                     for t in self.ckanmeta['timerange']]
         
        self.output['resource'].append(
            {'dates': submitted + collected}
        )

    def xs_language(self):
        # We assume an anglophonic world
        self.output['resource'].append({'language': 'en'})

    def xs_alternateIdentifiers(self):
        # Not implemented
        return

    def xs_relatedIdentifiers(self):
        # We scan the 'description' field of all resources
        # for a simple custom format
        descriptions = [(r.get('url'),
                         r.get('description'),
                         r.get('resource_type'))
                        for r in self.ckanmeta['resources']]
        relatedIdentifiers = []
        for d in descriptions:
            lines = re.split(r'\s*\r\n', d[1])
            lines = [l.strip() for l in lines]
            if lines[0] == 'relatedIdentifier':
                rel_types = re.sub(r'relationTypes:\s*', '', lines[2])
                rel_types = rel_types.split(',')
                rel_types = [rt.strip() for rt in rel_types]
                rel_id_type = re.sub(r'relatedIdentifierType:\s*', '', lines[1])
                rel_id_type = rel_id_type.strip()

                relatedIdentifiers += [
                    {'relatedIdentifier':
                     {'val': d[0],
                      'att': {'resourceTypeGeneral': d[2],
                              'relatedIdentifierType': rel_id_type,
                              'relationType': rt}}} for rt in rel_types]
        if relatedIdentifiers:
            self.output['resource'].append({'relatedIdentifiers':
                                            relatedIdentifiers})
            
    def xs_sizes(self):
        # Not implemented
        return
    
    def xs_formats(self):
        # Not implemented
        return
    
    def xs_version(self):
        version = input('Version [1.0]: ')
        version = '1.0' if version == '' else version
        self.output['resource'].append({'version': version})

    def xs_rightslist(self):
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

    def xs_descriptions(self):
        # We only consider descriptionType "Abstract"
        abstract = self.ckanmeta['notes']
        abstract = re.sub(r'\s*\r\n', '<b>', abstract)
        descriptions = {'descriptions': [
            {'description': {'val': abstract,
                             'att': {'descriptionType': 'Abstract',
                                     'lang': 'en'}
                             }}]}
        self.output['resource'].append(descriptions)

    def xs_geolocations(self):
        # Currently only implemented:
        # + geoLocationPoint
        # + geoLocationPlace
        #
        # Note that CKAN notation is lon/lat, whereas DataCite is lat/lon
        #
        # We do not use the posibility to have multiple geoLocations,
        # because we can't distinguish them in CKAN metadata.
        geo_location = []
        geonames = self.ckanmeta.get('geographic_name')
        for nam in geonames:
            geo_location.append({'geoLocationPlace': nam})
            
        spatial = json.loads(self.ckanmeta['spatial'])
        if spatial['type'] == 'Point':
            lon = spatial['coordinates'][0]
            lat = spatial['coordinates'][1]
            geo_location.append({'geoLocationPoint': [
                {'pointLongitude': str(lon)}, {'pointLatitude': str(lat)}
                ]})
        if geo_location:
            geoLocations = {'geoLocations': [{'geoLocation': geo_location}]}
        self.output['resource'].append(geoLocations)

    def xs_fundingReferences(self):
        # Not implemented
        return

    def main(self):
        funcnames = ['xs_{}'.format(e[1]) for e in self.elements()]
        for f in funcnames:
            getattr(self, f)()
        with open(self.outfile, 'w') as f_out:
            json.dump(self.output, f_out)

if __name__ == '__main__':
    args = docopt(__doc__, argv=sys.argv[1:])
    print(args)
    C = CKANExtract(args['<package_name>'], args['<doi>'], args['<outputfile>'])
    C.main()
