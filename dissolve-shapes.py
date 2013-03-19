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

groupByOperations = {
  'sum': (lambda x: sum(x), 'float'),
  'min': (lambda x: min(x), 'float'),
  'max': (lambda x: max(x), 'float'),
  'count': (lambda x: len(x), 'float'),
  'join': (lambda x: ','.join(x), 'str'),
  'first': (lambda x: x[0],),
  'last': (lambda x: x[-1],),
}
def getGroupByOp(op):
  o = groupByOperations[op]
  return o[0]

parser = OptionParser()
parser.add_option('-i', '--input', dest='input',
                  help='shapefile to read', metavar='FILE')
parser.add_option('-o', '--output', dest='output',
                  help='shapefile to write', metavar='FILE')
parser.add_option('-f', '--fields', dest='fields', metavar='f1,f2,f3',
  help='comma separated list of field names in the shapefile to group by and write out')
parser.add_option('-c', '--collectors', dest='collectors', action="append", default=[],
  metavar='inputKey:op:outputKey',
  help='arbitrarily collect fields across group by. op is one of %s' % (','.join(groupByOperations.keys())))

(options, args) = parser.parse_args()

matchingFields = []
collectorFields = {}

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
  collectorFields = defaultdict(list)
  geometryBuckets = defaultdict(list)
  propBuckets = defaultdict(lambda : defaultdict(list))
  collectorOutputOps = {}

  with collection(options.input, 'r') as input:
    originalSchema = input.schema.copy()
    print "original schema"
    print '  %s' % originalSchema
    newSchema = {}
    newSchema['geometry'] = 'MultiPolygon' 

    def getActualProperty(propName):
      actualField = [sf for sf in originalSchema['properties'].keys() if propName.strip().upper() == sf.upper()]
      if not actualField:
        print 'field %s not found in shapefile. possible values: %s' % (f, ','.join(schema['properties'].keys()))
        sys.exit(1)
      else:
        return str(actualField[0])

    matchingFields = [getActualProperty(f) for f in options.fields.split(',')]
    newSchema['properties'] = dict((key,value) for key, value in originalSchema['properties'].iteritems() if key in matchingFields)

    for c in options.collectors:
      parts = c.split(':')
      field = parts[0]
      op = parts[1]
      outField = field
      if len(parts) >= 2:
        outField = parts[2]

      if op not in groupByOperations.keys():
        print "op %s not found in groupByOperations: %s" % (op, ','.join(groupByOperations.keys()))
      if outField.upper() in [m.upper() for m in matchingFields]:
        print "cannot have field in both group by and collect: %s" % outField
        sys.exit(1)
      # oh god this should be a class not a tuple
      collectorFields[getActualProperty(field)].append(outField)
      collectorOutputOps[outField] = op
      print outField
      if len(groupByOperations[op]) == 2:
        newSchema['properties'][outField] = groupByOperations[op][1]
      else:
        newSchema['properties'][outField] = originalSchema['properties'][getActualProperty(field)]
      print 'collecting %s into %s with operator %s' % (getActualProperty(field), outField, op)
    print 'grouping by: %s' % matchingFields

  print "modified schema:"
  print '  %s' % newSchema

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
      for inputKey,outputKeys in collectorFields.iteritems():
        for outputKey in outputKeys:
          propBuckets[buildKeyFromFeature(f)][outputKey].append(f.GetField(inputKey))
      geometryBuckets[buildKeyFromFeature(f)].append(loads(g.ExportToWkb()))

  print 'saw %d features, made %d dissolved features' % (featuresSeen, len(geometryBuckets))

  with collection(
      options.output, 'w', 'ESRI Shapefile', newSchema) as output:
    for key, value in geometryBuckets.items():
      merged = cascaded_union(value)
      properties = json.loads(key)
      groupByPropMap = propBuckets[key]
      for f,values in groupByPropMap.iteritems():
        properties[f] = getGroupByOp(collectorOutputOps[f])(values)

      output.write({
        'properties': properties,
        'geometry': mapping(merged)
      })

processInput()
