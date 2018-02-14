# _*_ coding: utf-8 _*_

''' This module reads a json-file which contains the metadata of an
item to be published and returns a XML representation thereof.

Currently the application is DOI-minting and the DataCite metadata-schema v4.1
(https://schema.datacite.org/meta/kernel-4.1/metadata.xsd) is returned. (This
of course only happens if the input-metadata is DataCite compatible.)

The item's metadata in json is represented with regard to the XML nodes of
the schema:

Each XML node is represented by an object ("node-object").
Each node-object contains only one key - value pair.
The key of a node-object corresponds to an XML tag-name.
Namespaces for tag-names are expressed in Clark's notation:
http://www.jclark.com/xml/xmlns.htm.
The value of a node-object can be a (1) string, (2) an array or (3) an object.

(1) and (2) are simpliifcations, (3) Is most flexible. 

(1) In case it is a string, it equals the XML node's text. The node
does not have attributes or children.

(2) In case it is an array, the array contains node-objects of the node's children.
The node does not have text or attributes.

(3) In case it is an object, it might contain keys "val", "att", "children".

  + The value of "val" is a string and equals the XML node's text.
  + The value of "att" is an object and corresponds the the node's attributes.
    Namespaces for attributes are given using Clark's notation:
    http://www.jclark.com/xml/xmlns.htm.
  + The value of "children" is an array that contains node-objects of the node's
    children.

'''


import json
from lxml import etree as ET
from lxml.builder import ElementMaker

E = ElementMaker(nsmap={None: "http://datacite.org/schema/kernel-4"}) 

class MetaDataWriter:
    def __init__(self, metafile, typ='datacite4.1'):
        self.typ = typ
        self.schema = self._mk_schema(self.typ)
        self.attribute_defaults = self._mk_attribute_defaults(self.typ)
        self.attribute_map = self._mk_attribute_map(self.typ)
        self.meta = self._readmeta(metafile)
        self.root = self._build_tree()
        self._validate()
        

    def _validate(self):
        valid = self.schema.validate(ET.fromstring(ET.tostring(self.root)))
        print("Validation passed: {}".format(valid))
        if not valid:
            print(self.schema.error_log)
        
    def _readmeta(self, filename):
        'Reads metadata from (json) file'
        with open(filename, 'r') as f:
            return json.load(f)

    def writexml(self, filename=None):
        'Writes the final XML'
        if filename:
            xml = ET.tostring(self.root, encoding='utf-8',
                              xml_declaration=True)
            with open(filename, 'w') as f:
                f.write(xml.decode('utf-8'))
        else:
            xml = ET.tostring(self.root, encoding='utf-8',
                              xml_declaration=True,
                              pretty_print=True)
            print(xml.decode('utf-8'))
            
    def _mk_attribute_map(self, typ):
        if typ == 'datacite4.1':
            return {
                'lang': '{http://www.w3.org/XML/1998/namespace}lang',
            }
        else:
            return {}

    def _mk_attribute_defaults(self, typ):
        if typ == 'datacite4.1':
            return {
                'resource': {
                    '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':
                    'http://datacite.org/schema/kernel-4 '
                    'http://schema.datacite.org/meta/kernel-4.1/metadata.xsd'
                }
            }
        else:
            return {}

    def _mk_schema(self, typ):
        if typ == 'datacite4.1':
            return ET.XMLSchema(
                ET.parse('schema/datacite/metadata_schema_4.1.xsd')
            )
    
    def _build_tree(self, d=None):
        "Traverses the json-metadata and builds the corresponding lxml-tree"
        d = d or self.meta
        assert len(d) == 1
        k = list(d.keys())[0]
        v = list(d.values())[0]
        default_att = self.attribute_defaults.get(k)
        if isinstance(v, str):
            # simple element
            el = E(k)
            el.text = v
            if default_att:
                el.attrib.update(default_att)
            return el
        if isinstance(v, list):
            # element containing sequence of child elements / no attributes
            el = E(k)
            for child in v:
                el.append(self._build_tree(d=child))
            if default_att:
                el.attrib.update(default_att)
            return el
        if isinstance(v, dict):
            # element with attribute(s)
            el = E(k)
            att = v.get('att') 
            if att:
                att = {self.attribute_map.get(k) or k: v for k, v in att.items()}
                el.attrib.update(att)
            if default_att:
                el.attrib.update(default_att)
            if v.get('val'):
                el.text =  v.get('val')
            children = v.get('children', [])
            for child in children:
                el.append(self._build_tree(d=child))
            return el

if __name__ == "__main__":
    dmw = MetaDataWriter('metadata/snsf_dmp_guide.json')
    dmw.writexml('output/datacite/snsf_dmp_guide.xml')




