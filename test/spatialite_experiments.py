import sip

sip.setapi('QString', 2)  # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from pyspatialite import dbapi2 as db
from qgis.core import *

from datetime import datetime, timedelta
import os
import unittest
from TimeManager.time_util import datetime_to_str, DEFAULT_FORMAT
from test_functionality import TestWithQGISLauncher, RiggedTimeManagerControl
import TimeManager.time_util as time_util
import TimeManager.timevectorlayer as timevectorlayer
from TimeManager.query_builder import STRINGCAST_FORMAT, INT_FORMAT, STRING_FORMAT
from TimeManager.layer_settings import LayerSettings
from mock import Mock


STARTTIME = 1420746289  # 8 January 2015
TEST_TABLE = "test_table"
DB_FILE = "testdata/test_db.sqlite"
DB_FILE_WITH_DATETIMES = "testdata/data_with_datetime.sqlite"
INTEGER_TIMESTAMP = "epoch_seconds"
STRING_TIMESTAMP = "datetime"
NUM_PTS = 100

"""Some test cases for Spatialite which do not build on Travis at the moment"""


class TestSpatialite(TestWithQGISLauncher):
    comparison_op = "<"

    @classmethod
    def setUpClass(cls):
        super(TestSpatialite, cls).setUpClass()
        create_point_db(DB_FILE, TEST_TABLE, STARTTIME, NUM_PTS)

    @classmethod
    def tearDownClass(cls):
        super(TestSpatialite, cls).tearDownClass()
        # os.remove(DB_FILE)

    def setUp(self):
        super(TestSpatialite, self).setUp()
        self.layer = self._load_spatialite_layer(DB_FILE, "test_table", "geom", NUM_PTS)
        # this spatialite layer can only be loaded as a vector layer
        self.layer_loaded_as_vector = QgsVectorLayer(DB_FILE, "pointz_vector", 'ogr')
        # this spatialite layer can only be loaded as a vector layer
        self.layer_dtimes = QgsVectorLayer(DB_FILE_WITH_DATETIMES, "dtimes", 'ogr')
        self.assertTrue(self.layer_dtimes.isValid())

    def _load_spatialite_layer(self, file, table, geom_col, cnt, name="pointz"):
        uri = QgsDataSourceURI()
        uri.setDatabase(file)
        uri.setDataSource('', table, geom_col, '')
        layer = QgsVectorLayer(uri.uri(), name, 'spatialite')
        self.assertTrue(layer.isValid())
        self.assertEquals(layer.featureCount(), cnt)
        self.assertEquals(layer.subsetString(), '')
        return layer

    def test_datetime_loaded_by_sqlite(self):
        self._test_spatialite_layer(STRING_TIMESTAMP, self.layer, is_int=False)

    def test_int_loaded_by_sqlite(self):
        self._test_spatialite_layer(INTEGER_TIMESTAMP, self.layer, is_int=True)

    def test_datetime_loaded_by_vector(self):
        layer = self.layer_loaded_as_vector
        attr = STRING_TIMESTAMP
        settings = LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = attr
        settings.endTimeAttribute = attr
        timeLayer = timevectorlayer.TimeVectorLayer(settings, iface=Mock())
        self.tlm.registerTimeLayer(timeLayer)

        self.assertEquals(timeLayer.getDateType(), timevectorlayer.DateTypes.DatesAsQDateTimes)

    def test_datetime_loaded_by_vector2(self):
        """Testing for the file provided by https://github.com/henrikkriisa"""
        layer = self.layer_dtimes
        attr = "measuredts"
        settings = LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = attr
        settings.endTimeAttribute = attr
        timeLayer = timevectorlayer.TimeVectorLayer(settings, iface=Mock())
        self.tlm.registerTimeLayer(timeLayer)

        self.assertEquals(timeLayer.getDateType(), timevectorlayer.DateTypes.DatesAsQDateTimes)
        self.tlm.setTimeFrameType("minutes")
        self.tlm.stepForward()
        subsetString = layer.subsetString()
        expectedSubsetString = STRINGCAST_FORMAT.format(attr, self.comparison_op,
                                                        time_util.datetime_to_str(
                                                            self.tlm.getCurrentTimePosition() + timedelta(
                                                                minutes=1)
                                                            , timeLayer.getTimeFormat()), attr,
                                                        time_util.datetime_to_str(
                                                            self.tlm.getCurrentTimePosition(),
                                                            timeLayer.getTimeFormat()))
        self.assertEqual(timeLayer.getTimeFormat(), time_util.OGR_DATETIME_FORMAT)
        self.assertEquals(subsetString, expectedSubsetString)


    # FIXME here the behavior is odd. Skipping for now
    @unittest.skip
    def test_add_same_layer_twice(self):
        self._test_spatialite_layer(STRING_TIMESTAMP, is_int=False)
        self._test_spatialite_layer(INTEGER_TIMESTAMP, is_int=True)


    def _test_spatialite_layer(self, attr, layer, is_int=False):

        settings = LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = attr
        settings.endTimeAttribute = attr

        timeLayer = timevectorlayer.TimeVectorLayer(settings, iface=Mock())
        self.tlm.registerTimeLayer(timeLayer)
        if is_int:
            self.assertEquals(timeLayer.getDateType(), timevectorlayer.DateTypes.IntegerTimestamps)
            self.assertEquals(timeLayer.getTimeFormat(), time_util.UTC)
        else:
            self.assertEquals(timeLayer.getDateType(), timevectorlayer.DateTypes.DatesAsStrings)
            self.assertEquals(timeLayer.getTimeFormat(), time_util.DEFAULT_FORMAT)
        start_time = time_util.str_to_datetime(timeLayer.getMinMaxValues()[0], time_util.PENDING)
        self.assertEquals(time_util.epoch_to_datetime(STARTTIME), start_time)

        self.tlm.setTimeFrameType("minutes")
        self.tlm.stepForward()
        assert ( start_time + timedelta(minutes=1) == self.tlm.getCurrentTimePosition())
        # only one feature is selected now, because there is one feature per minute
        self.assertEquals(layer.featureCount(), 1)
        FS = 5
        self.tlm.setTimeFrameSize(FS)
        # we have one feature per minute
        self.assertEquals(layer.featureCount(), FS)
        subsetString = layer.subsetString()

        if is_int:
            expectedSubsetString = INT_FORMAT.format(attr, self.comparison_op,
                                                     time_util.datetime_to_epoch(
                                                         self.tlm.getCurrentTimePosition() + timedelta(
                                                             minutes=FS)),
                                                     attr,
                                                     time_util.datetime_to_epoch(
                                                         self.tlm.getCurrentTimePosition()))

            self.assertEquals(subsetString, expectedSubsetString)
            minimum_bound_seconds = int(subsetString.split(" ")[6])
            self.assertEquals(self.tlm.getCurrentTimePosition(), time_util.epoch_to_datetime(
                minimum_bound_seconds))
        if not is_int:
            self.assertEqual(timeLayer.getTimeFormat(), time_util.DEFAULT_FORMAT)
            expectedSubsetString = STRING_FORMAT.format(attr, self.comparison_op,
                                                        time_util.datetime_to_str(
                                                            self.tlm.getCurrentTimePosition() + timedelta(
                                                                minutes=FS)
                                                            , timeLayer.getTimeFormat()), attr,
                                                        time_util.datetime_to_str(
                                                            self.tlm.getCurrentTimePosition(),
                                                            timeLayer.getTimeFormat()))

            self.assertEquals(subsetString, expectedSubsetString)

        self.tlm.stepForward()
        self.assertEquals(layer.featureCount(), FS)


def create_point_db(dest, dbname, starttime, num_items):
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
    # print "Spatialite initialized"
    # creating a POINT table
    sql = 'CREATE TABLE %r (' % (dbname)
    sql += '{} INTEGER NOT NULL PRIMARY KEY,'.format(INTEGER_TIMESTAMP)
    sql += 'name TEXT NOT NULL,'
    sql += '{} DATETIME NOT NULL)'.format(STRING_TIMESTAMP)
    cur.execute(sql)
    # creating a POINT Geometry column
    sql = "SELECT AddGeometryColumn('%s'," % (dbname)
    sql += "'geom', 4326, 'POINT', 2)"
    cur.execute(sql)

    # inserting num_items points
    for i in range(0, num_items):
        name = "test POINT #%d" % (i + 1)
        curr_time_epoch = starttime + i * 60
        curr_datetime = datetime.utcfromtimestamp(curr_time_epoch)
        geom = "GeomFromText('POINT("
        geom += "%f " % (-10.0 - (i / 10.0))
        geom += "%f" % (+10.0 + (i / 10.0))
        geom += ")', 4326)"
        print geom
        sql = "INSERT INTO {} ({}, name, geom, {}) ".format(dbname, INTEGER_TIMESTAMP,
                                                            STRING_TIMESTAMP)
        sql += "VALUES (%d, '%s', %s, '%s')" % (
        curr_time_epoch, name, geom, datetime_to_str(curr_datetime, DEFAULT_FORMAT))
        cur.execute(sql)
        conn.commit()


if __name__ == "__main__":
    unittest.main()
    QgsApplication.exitQgis()  #FIXME nosetests is brittle that way
