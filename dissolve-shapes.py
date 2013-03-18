#!/usr/bin/python

from osgeo import ogr
from shapely.wkb import loads
from collections import defaultdict
from shapely.geometry import mapping, shape
from shapely.ops import cascaded_union
from fiona import collection
import json
import sys
from optparse import OptionParser

parser = OptionParser()
parser.add_option('-i', '--input', dest='input',
                  help='shapefile to read', metavar='FILE')
parser.add_option('-o', '--output', dest='output',
                  help='shapefile to write', metavar='FILE')
parser.add_option('-f', '--fields', dest='fields', metavar='f1,f2,f3',
  help='comma separated list of field names in the shapefile to group by and write out')

(options, args) = parser.parse_args()

matchingFields = []

# we build the key as the string representation of the json representation of the
# dict of keys that we grouped by (and intend to save) dictionaries aren't hashable,
# and this was an easy way to keep the full dict next to the geometries
def buildKeyFromFeature(feature):
  values = {}
  for field in matchingFields:
    value = feature.GetField(field)
    if not value:
      raise Exception('missing field %s on feature %s' % (field, feature))
    else:
      values[field] = value

  return json.dumps(values)

def processInput():
  global matchingFields
  geometryBuckets = defaultdict(list)

  with collection(options.input, 'r') as input:
    schema = input.schema.copy()
    print "original schema"
    print '  %s' % schema
    schema['geometry'] = 'MultiPolygon' 

    for f in options.fields.split(','):
      actualField = [sf for sf in schema['properties'].keys() if f.strip().upper() == sf.upper()]
      if not actualField:
        print 'field %s not found in shapefile. possible values: %s' % (f, ','.join(schema['properties'].keys()))
        sys.exit(1)
      else:
        matchingFields.append(str(actualField[0]))
    print 'grouping by: %s' % matchingFields

    schema['properties'] = dict((key,value) for key, value in schema['properties'].iteritems() if key in matchingFields)
  print "modified schema:"
  print '  %s' % schema

  ds = ogr.Open(options.input)
  inputShape = ds.GetLayer(0)
  print 'examining %s, with %d features' % (options.input, inputShape.GetFeatureCount())
  featuresSeen = 0
  # using raw shapely here because fiona barfs on invalid geoms in the shapefile
  while True:
    featuresSeen += 1
    f = inputShape.GetNextFeature()
    if f is None: break
    g = f.geometry()
    if g is not None:
      geometryBuckets[buildKeyFromFeature(f)].append(loads(g.ExportToWkb()))

  print 'saw %d features, made %d dissolved features' % (featuresSeen, len(geometryBuckets))

  with collection(
      options.output, 'w', 'ESRI Shapefile', schema) as output:
    for key, value in geometryBuckets.items():
      merged = cascaded_union(value)
      output.write({
        'properties': json.loads(key),
        'geometry': mapping(merged)
      })

processInput()
