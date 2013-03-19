#!/usr/bin/python

from osgeo import ogr
from shapely.wkb import loads
from collections import defaultdict
from shapely.geometry import mapping, shape
from shapely.ops import cascaded_union
import json
import sys
from optparse import OptionParser
from rtree import Rtree
from merge_utils import *

parser = OptionParser()
parser.add_option('--point', '--point-input', dest='point_input',
                  help='shapefile to read points', metavar='FILE')
parser.add_option('--poly',  '--poly-input', dest='poly_input',
                  help='shapefile to read polys', metavar='FILE')
parser.add_option('--o',  '--output', dest='output',
                  help='output filename', metavar='FILE')
parser.add_option('--poly-fields', dest='poly_fields',
                  help='comma separated list of fields to copy from polygon feature')
parser.add_option('-c', '--collector', dest='collectors', action="append", default=[],
  metavar='inputKey:op:outputKey',
  help='arbitrarily collect fields from point input. op is one of %s' % (','.join(groupByOperations.keys())))
parser.add_option('-r', '--radius', dest='radius', default=None, type='float',
                  help='optional radius in meters argument for point testing')

(options, args) = parser.parse_args()

def checkArg(opt, message):
  if not opt:
    print "Missing %s" % message
    parser.print_usage()
    sys.exit(1)

checkArg(options.output, 'output')
checkArg(options.poly_input, 'poly input')
checkArg(options.point_input, 'point input')

if not options.output:
  missing_opt("output")

def processInput():
  index = Rtree('/tmp/polyRtree')
  featureIndex = {}

  with collection(options.poly_input, 'r') as poly_input:
    originalSchema = poly_input.schema.copy()
    print "original schema"
    print '  %s' % originalSchema
    newSchema = filterFionaSchema(poly_input, options.poly_fields.split(','))
    inputCRS = poly_input.crs
    collectors = Collectors(poly_input, options.collectors)
    collectors.addToFionaSchema(newSchema)
    print "new schema\n%s" % newSchema
  
    print "loading %d polygons into rtree" % len(poly_input)
    for i, f in enumerate(poly_input):
      if i % 1000 == 0:
        print "finished %d of %d poly" % (i, len(poly_input))

      index.add(i, shape(f['geometry']).bounds)
      featureIndex[i] = f

  with collection(options.point_input, 'r') as point_input:
    print "checking %d points against rtree" % len(point_input)

    for i, pointFeature in enumerate(point_input):
      testShape = shape(pointFeature['geometry'])
      if i % 100 == 0:
        print "finished %d of %d points" % (i, len(point_input))
      
      if (options.radius):
        radiusDegrees = options.radius / 111131.745
        testShape = testShape.buffer(radiusDegrees, 30)

      matches = index.intersection(testShape.bounds)
      for polyIndex in matches:
        polyFeature = featureIndex[polyIndex]
        if shape(polyFeature['geometry']).intersects(testShape):
          collectors.recordMatch(polyIndex, pointFeature)

  with collection(
      options.output, 'w', 'ESRI Shapefile', newSchema, crs=inputCRS) as output:
   
    for key, feature in featureIndex.items():
      properties = { your_key: feature['properties'][your_key] for your_key in feature['properties'].keys() if your_key in newSchema.keys() }
      collectors.outputMatchesToDict(key, properties)
      if len(properties.keys()) == len(newSchema['properties'].keys()):
        output.write({
          'properties': properties,
          'geometry': mapping(shape(feature['geometry']))
        })
      else:
        print "no matches for: %s" % key

processInput()
