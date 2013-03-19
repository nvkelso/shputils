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

def getActualProperty(collection, propName):
  originalSchema = collection.schema
  actualField = [sf for sf in originalSchema['properties'].keys() if propName.strip().upper() == sf.upper()]
  if not actualField:
    print 'field %s not found in shapefile. possible values: %s' % (f, ','.join(schema['properties'].keys()))
    sys.exit(1)
  else:
    return str(actualField[0])

def filterFionaSchema(collection, keys):
  newSchema = collection.schema.copy()
  matchingFields = [getActualProperty(collection, f) for f in keys]
  newSchema['properties'] = dict((key,value) for key, value in collection.schema['properties'].iteritems() if key in matchingFields)
  return newSchema

class Collectors:
  def __init__(self, collection, collectorStrs):
    self.collectors = [Collector(collection, c) for c in collectorStrs]

  def recordMatch(self, groupKey, f):
    for c in self.collectors:
      c.recordMatch(groupKey, f)

  def outputMatchesToDict(self, groupKey, output):
    for c in self.collectors:
      output[c.outputField] = c.getOutput(groupKey)

  def outputMatches(self):
    output = {}
    outputMatchesToDict(output)
    return output

  def addToFionaSchema(self, schema):
    for c in self.collectors:
      schema['properties'][c.outputField] = c.outputType 

class Collector:
  def __init__(self, collection, inputStr):
    parts = inputStr.split(':')
    self.inputField = getActualProperty(collection, parts[0])
    self.op = parts[1]
    self.outputField = self.inputField
    if len(parts) >= 2:
      self.outputField = parts[2]

    self.matches = defaultdict(list)
    if self.op not in groupByOperations.keys():
      print "op %s not found in groupByOperations: %s" % (self.op, ','.join(groupByOperations.keys()))

    if len(groupByOperations[self.op]) == 2:
      self.outputType = groupByOperations[self.op][1]
    else:
      self.outputType = collection.schema['properties'][self.inputField]
    print 'collecting %s into %s with operator %s' % (self.inputField, self.outputField, self.op)

  def recordMatch(self, groupKey, f):
    # assume it's shapely
    if hasattr(f, 'GetField'):
      self.matches[groupKey].append(f.GetField(self.inputField))
    else:
      # assume it's fiona
      self.matches[groupKey].append(f['properties'][self.inputField])

  def getOutput(self, groupKey):
    if self.matches[groupKey]:
      return getGroupByOp(self.op)(self.matches[groupKey])
    else:
      return None

