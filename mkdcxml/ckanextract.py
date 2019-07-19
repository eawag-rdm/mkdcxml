# _*_ coding: utf-8 _*_

# This module requires Python >= 3.5
# © 2018, Harald von Waldow @ Eawag

# This program is licensed under the
# GNU AFFERO GENERAL PUBLIC LICENSE version 3
# https://www.gnu.org/licenses/agpl.txt


'''ckanextract

Usage:
  ckanextract [-s <hosturl>] [--affils=<affilmap>] [--orcids=<orcids>]
              [--related_identifiers=<relids>] <doi> <package_name> <outputfile>
  ckanextract -h

Options:
  --server, -s <hosturl>           The url of the CKAN instance.
                                   [default: https://data.eawag.ch] 
  --help, -h                       Show this screen
  --affils=<affilmap>              Read affiliations of authors from <affilamp>.
                                   Else, interactve input.
  --orcids=<orcids>                Reads ORCIDs from file, else interactive input.
  --related_identifiers=<relids>   Reads related identifiers from file.

Arguments:
  <doi>          DOI in the form "10.25678/000011"
  <package_name> The CKAN package name
  <outputfile>   The file to which the intermediate json is written
  <affilmap>     JSON file that map author to affiliation:
                 {
                   "Lastname, Firstname": "affiliation",
                    ....
                 }
  <orcids>       JSON file that maps authors to ORCIDs:
                 {
                   "Lastname, Firstname": "ORCID",
                    ....
                 }
  <relids>       JSON file with related idetifiers:
                 [
                   {"relatedIdentifier":
                     {"val": "e.g. a DOI",
                      "att": {
                               "resourceTypeGeneral": "TEXT",
                               "relatedIdentifierType": "DOI",
	                       "relationType": "Cites"
                             }
                     }
                   },
                   ....
                 ]  


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

CKANAPIKEY = os.environ['CKAN_APIKEY_PROD1']
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

        
    def __init__(self, pkgname, doi, outfile, server, affils, orcids, relids):
        self.pkgname = pkgname
        self.server = server
        self.ckanmeta = self.get_ckanmeta(pkgname)
        self.doi = doi
        self.output = {'resource': []}
        self.outfile = outfile
        self.affils = json.load(open(affils, 'r')) if affils else None
        self.orcids = json.load(open(orcids, 'r')) if orcids else None
        self.related_identifiers_from_file = (json.load(open(relids, 'r'))
                                              if relids else None)

    def get_ckanmeta(self, pkgname):
        with ckanapi.RemoteCKAN(self.server, apikey=CKANAPIKEY) as conn:
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
            fullname = '{}, {}'.format(last, rest)
            if not self.orcids:
                orcid = input('Author: |{}| email:|{}| : ORCID: '
                              .format(fullname, email))
            else:
                try:
                    orcid = self.orcids[fullname]
                    print('Found ORCID {} for "{}"'.format(orcid, fullname))
                except KeyError:
                    orcid = None
            if not self.affils:
                eawag = input('Affiliation Eawag? [Y/n]')
                eawag = True if eawag in ['', 'Y', 'y', '1'] else False
                affiliation = DEFAULT_AFFILIATION if eawag else None
            else:
                try:
                    affiliation = self.affils[fullname]
                    print('Found affiliation "{}" for "{}"'
                          .format(affiliation, fullname))
                except KeyError:
                    affiliation = None
                    
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
            if affiliation:
                creator.append(
                    {'affiliation': affiliation}
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
                
        if self.related_identifiers_from_file:
            relatedIdentifiers += self.related_identifiers_from_file
                    
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

    def _description_parse(self, desc):
        # creates a list of br-elements (<children>) with appropriate tails
        # and a string <text>, representing the text-value of the parent.
        
        texts = desc.split('\r\n')
        text = texts.pop(0)
        children = [{'br': {'val': '', 'tail': t}} for t in texts]
        return (text, children)

    def xs_descriptions(self):
        # We only consider descriptionType "Abstract"
        abstract = self.ckanmeta['notes']
        text, children = self._description_parse(abstract)
        descriptions = {'descriptions': [
            {'description': {'val': text,
                             'att': {'descriptionType': 'Abstract',
                                     'lang': 'en'},
                             'children': children}}
            ]}
        self.output['resource'].append(descriptions)

    def xs_geolocations(self):
        # Currently only implemented:
        # + geoLocationPoint
        # + geoLocationPlace
        # + geoLocation - MultiPoint
        #
        # Note that CKAN notation is lon/lat.
        #
        # Each geoLocation-feature (place, point) is one geoLocation. 
        # The spec seems to allow to accociate, say a geoname and a point,
        # but we can't do that in CKAN anyway, and I don't really understand
        # the XML (xs:choice).
        
        geo_locations = []
        
        geonames = self.ckanmeta.get('geographic_name')
        for nam in geonames:
            geo_locations.append(
                {'geoLocation': [{'geoLocationPlace': nam}]}
            )

        def mk_point_location(lon, lat):
            point_location = {
                'geoLocation': [
                    {'geoLocationPoint': [{'pointLongitude': str(lon)},
                                          {'pointLatitude': str(lat)}]
                    }]
            }
            return point_location
            
        spatial = json.loads(self.ckanmeta.get('spatial'))
        if spatial:
            if spatial['type'] == 'Point':
                lon = spatial['coordinates'][0]
                lat = spatial['coordinates'][1]
                geo_locations.append(mk_point_location(lon, lat))
                
            if spatial['type'] == 'MultiPoint':
                pointlist = []
                for point in spatial['coordinates']:
                    lon = point[0]
                    lat = point[1]
                    geo_locations.append(mk_point_location(lon, lat))

        if geo_locations:
            self.output['resource'].append({'geoLocations': geo_locations})
        

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
    C = CKANExtract(args['<package_name>'], args['<doi>'],
                    args['<outputfile>'], args['--server'],
                    args['--affils'], args['--orcids'],
                    args['--related_identifiers'])
    C.main()
