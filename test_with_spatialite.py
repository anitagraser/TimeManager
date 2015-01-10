import sip
sip.setapi('QString', 2) # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from pyspatialite import dbapi2 as db
from qgis.core import *

from datetime import datetime, timedelta
import os
import unittest
from time_util import datetime_to_str, DEFAULT_FORMAT
from test_functionality import TestWithQGISLauncher, RiggedTimeManagerControl
import time_util
import timevectorlayer
from mock import Mock


STARTTIME=1420746289 # 8 January 2015
TEST_TABLE="test_table"
DB_FILE="testdata/test_db.sqlite"
INTEGER_TIMESTAMP ="epoch_seconds"
STRING_TIMESTAMP="datetime"
NUM_PTS = 100

class TestSpatialite(TestWithQGISLauncher):

    @classmethod
    def setUpClass(cls):
        super(TestSpatialite, cls).setUpClass()
        create_point_db(DB_FILE, TEST_TABLE, STARTTIME, NUM_PTS)

    @classmethod
    def tearDownClass(cls):
        super(TestSpatialite,cls).tearDownClass()
        #os.remove(DB_FILE)


    def setUp(self):
        iface = Mock()
        self.ctrl = RiggedTimeManagerControl(iface)
        self.ctrl.initGui(test=True)
        self.tlm = self.ctrl.getTimeLayerManager()
        self.layer = self._load_spatialite_layer()

    def _load_spatialite_layer(self):
        uri = QgsDataSourceURI()
        uri.setDatabase(DB_FILE)
        uri.setDataSource('', TEST_TABLE,'geom','')
        layer = QgsVectorLayer(uri.uri(),'pointz', 'spatialite')
        self.assertTrue(layer.isValid())
        self.assertEquals(layer.featureCount(), NUM_PTS)
        self.assertEquals(layer.subsetString(),'')
        return layer

    def test_spatialite_layer_integer_timestamps(self):

        attr = INTEGER_TIMESTAMP
        timeLayer = timevectorlayer.TimeVectorLayer(self.layer,attr,attr,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.tlm.registerTimeLayer(timeLayer)
        start_time = time_util.str_to_datetime(timeLayer.getMinMaxValues()[0], time_util.DEFAULT_FORMAT)
        self.assertEquals(time_util.epoch_to_datetime(STARTTIME), start_time)
        self.tlm.setTimeFrameType("minutes")
        self.tlm.stepForward()
        assert( start_time + timedelta(minutes=1)==self.tlm.getCurrentTimePosition())
        # only one feature is selected now, because there is one feature per minute
        self.assertEquals(self.layer.featureCount(), 1)
        FS = 5
        self.tlm.setTimeFrameSize(FS)
        self.assertEquals(self.layer.featureCount(), FS)
        subsetString = self.layer.subsetString()
        expectedSubsetString = "{} < {} AND {} >= {} ".format(attr,
                                time_util.datetime_to_epoch(self.tlm.getCurrentTimePosition()+timedelta(minutes=FS)),
                                attr,
                                time_util.datetime_to_epoch(self.tlm.getCurrentTimePosition()))
        self.assertEquals(subsetString, expectedSubsetString)
        minimum_bound_seconds = int(subsetString.split(" ")[6] )
        self.assertEquals(self.tlm.getCurrentTimePosition(), time_util.epoch_to_datetime(
            minimum_bound_seconds))
        self.tlm.stepForward()
        self.assertEquals(self.layer.featureCount(), FS)



if __name__=="__main__":
    unittest.main()
    QgsApplication.exitQgis() #FIXME nosetests is brittle that way

def create_point_db( dest, dbname, starttime, num_items):
    """
    Re-create the point db if it doesn't exist
    """

    if os.path.exists(dest):
        return

    # creating/connecting the test_db and getting a cursor
    conn = db.connect(dest)
    cur = conn.cursor()

    # initializing Spatial MetaData
    # using v.2.4.0 this will automatically create
    # GEOMETRY_COLUMNS and SPATIAL_REF_SYS
    sql = 'SELECT InitSpatialMetadata()'
    cur.execute(sql)
    #print "Spatialite initialized"
    # creating a POINT table
    sql = 'CREATE TABLE %r (' %(dbname)
    sql += '{} INTEGER NOT NULL PRIMARY KEY,'.format(INTEGER_TIMESTAMP)
    sql += 'name TEXT NOT NULL,'
    sql += '{} DATETIME NOT NULL)'.format(STRING_TIMESTAMP)
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
        sql = "INSERT INTO {} ({}, name, geom, {}) ".format(dbname, INTEGER_TIMESTAMP, STRING_TIMESTAMP)
        sql += "VALUES (%d, '%s', %s, '%s')" % (curr_time_epoch, name, geom,datetime_to_str(curr_datetime, DEFAULT_FORMAT))
        cur.execute(sql)
        conn.commit()
