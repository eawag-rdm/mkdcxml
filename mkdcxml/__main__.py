from mkdcxml import MetaDataWriter
from pkg_resources import resource_stream 

dmw = MetaDataWriter(resource_stream(__name__,
                                  'tests/metadata/snsf_dmp_guide.json'))
dmw.writexml(resource_stream(__name__,'tests/output/snsf_dmp_guide.xml'))
