shputils
========

dissolve-shapes
---------------
Used for joining multiple shapes in a shapefile based on exact matches between fields. Useful if you have a shapefile of counties, where each county lists its state, and you want to end up with shape polygons

    Usage: dissolve-shapes.py [options]

    Options:
      -h, --help            show this help message and exit
      -i FILE, --input=FILE
                            shapefile to read
      -o FILE, --output=FILE
                            shapefile to write
      -f f1,f2,f3, --fields=f1,f2,f3
                            comma separated list of field names in the shapefile
                            to group by and write out
      -c inputKey:op:outputKey, --collectors=inputKey:op:outputKey
                            arbitrarily collect fields across group by. op is one
                            of count,join,min,max,sum,last,first

point-matcher
-------------
Used for using a shapefile of points to name a shapefile of polys.

    Usage: point-matcher.py [options]

    Options:
      -h, --help            show this help message and exit
      --point=FILE, --point-input=FILE
                            shapefile to read points
      --poly=FILE, --poly-input=FILE
                            shapefile to read polys
      --o=FILE, --output=FILE
                            output filename
      --poly-fields=POLY_FIELDS
                            comma separated list of fields to copy from polygon
                            feature
      -c inputKey:op:outputKey, --collector=inputKey:op:outputKey
                            arbitrarily collect fields from point input. op is one
                            of count,join,min,max,sum,last,first
      -r RADIUS, --radius=RADIUS
                            optional radius in meters argument for point testing
