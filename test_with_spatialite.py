from pyspatialite import dbapi2 as db

from datetime import datetime
import os
from time_util import datetime_to_str, DEFAULT_FORMAT

starttime=1420746289 # 8 January 2015

TEST_DB_NAME="test_table"
DB_DEST="testdata/test_db.sqlite"

def create_point_db( dest, dbname, starttime, num_items):

    if os.path.exists(dest):
        os.remove(dest)
    # creating/connecting the test_db and getting a cursor
    conn = db.connect(dest)
    cur = conn.cursor()

    # # testing library versions
    #rs = cur.execute('SELECT sqlite_version(), spatialite_version()')
    #for row in rs:
    #    msg = "SQLite v%s Spatialite v%s" % (row[0], row[1])
    #    print msg

    # initializing Spatial MetaData
    # using v.2.4.0 this will automatically create
    # GEOMETRY_COLUMNS and SPATIAL_REF_SYS
    sql = 'SELECT InitSpatialMetadata()'
    cur.execute(sql)
    #print "Spatialite initialized"
    # creating a POINT table
    sql = 'CREATE TABLE %r (' %(dbname)
    sql += 'epoch_seconds INTEGER NOT NULL PRIMARY KEY,'
    sql += 'name TEXT NOT NULL,'
    sql += 'datetime DATETIME NOT NULL)'
    cur.execute(sql)
    # creating a POINT Geometry column
    sql = "SELECT AddGeometryColumn('%s'," %(dbname)
    sql += "'geom', 4326, 'POINT', 2)"
    cur.execute(sql)

    # inserting some points
    for i in range(0,num_items):
        name = "test POINT #%d" % (i+1)
        curr_time_epoch = starttime + i*60
        curr_datetime = datetime.utcfromtimestamp(curr_time_epoch)
        geom = "GeomFromText('POINT("
        geom += "%f " % (-10.0 - (i / 10.0))
        geom += "%f" % (+10.0 + (i / 10.0))
        geom += ")', 4326)"
        print geom
        sql = "INSERT INTO %s (epoch_seconds, name, geom, datetime) " % (dbname)
        sql += "VALUES (%d, '%s', %s, '%s')" % (curr_time_epoch, name, geom,datetime_to_str(curr_datetime, DEFAULT_FORMAT))
        cur.execute(sql)
        conn.commit()
