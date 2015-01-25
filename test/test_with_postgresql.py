import sip
sip.setapi('QString', 2) # strange things happen without this. Must import before PyQt imports
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
from mock import Mock
from nose.tools import raises

import psycopg2

DBNAME="mydb"
TABLE="pts"

GEOMETRY_COL="geom"
DATE_COL="_date"
DATE_TZ_COL="_datetz"
EPOCH_COL="epoch"
DATE_STR_COL="datestr"
DATE_STR_COL_DMY="datestr_dmy"

STARTTIME=time_util.datetime_to_epoch(datetime(2014,12,31,23,59,59))

SQL_STATEMENT="""
DROP TABLE IF EXISTS {0:s};
CREATE TABLE {0:s} (

   {1:s} geometry,
   {2:s} timestamp, -- date with time of day without timezone
   {3:s} timestamp with time zone, -- has timezone in format +xx
   {4:s} integer,
   {5:s} text,
   {6:s} text

);

insert into pts ({1:s},{2:s},{3:s},{4:s},{5:s},{6:s}) values (ST_MakePoint(1.0,1.02),NULL,NULL,
{7},NULL,NULL);
insert into pts ({1:s},{2:s},{3:s},{4:s},{5:s},{6:s}) values (ST_MakePoint(1.01,1.01),NULL,NULL,
{8},NULL,NULL);
insert into pts ({1:s},{2:s},{3:s},{4:s},{5:s},{6:s}) values (ST_MakePoint(1.02,1.01),NULL,NULL,
{9},NULL,NULL);
insert into pts ({1:s},{2:s},{3:s},{4:s},{5:s},{6:s}) values (ST_MakePoint(1.00,1.03),NULL,NULL,
{10},NULL,NULL);
insert into pts ({1:s},{2:s},{3:s},{4:s},{5:s},{6:s}) values (ST_MakePoint(1.0,1.04),NULL,NULL,
{11},NULL,NULL);
set timezone='UTC';
update pts set {2:s} = to_timestamp(epoch);
update pts set {3:s} = to_timestamp(epoch);
update pts set {5:s} = to_char(_date,'YYYY/MM/DD HH24:MI:SS');
update pts set {6:s} = to_char(_date,'DD.MM.YYYY HH24:MI:SS');
""".format(TABLE,GEOMETRY_COL,DATE_COL,DATE_TZ_COL,EPOCH_COL, DATE_STR_COL,
           DATE_STR_COL_DMY,STARTTIME,STARTTIME+1,STARTTIME+2,STARTTIME+3,STARTTIME+4)

CUSTOM_FORMAT="%Y/%m/%d %H:%M:%S"
CUSTOM_FORMAT_DMY="%d.%m.%Y %H:%M:%S"

class TestPostgreSQL(TestWithQGISLauncher):

    conn = None

    @classmethod
    def setUpClass(cls):
        super(TestPostgreSQL, cls).setUpClass()
        try:
            cls.conn = psycopg2.connect("dbname='mydb' user='postgres' host='localhost' "
                                        "password='postgres'")
            cls.conn.cursor().execute(SQL_STATEMENT)
            cls.conn.commit()
        except Exception, e:
            raise Exception(e)


    @classmethod
    def tearDownClass(cls):
        super(TestPostgreSQL,cls).tearDownClass()
        cls.conn.cursor().execute("DROP TABLE IF EXISTS {};".format(TABLE))
        cls.conn.close()

    def setUp(self):
        iface = Mock()
        self.ctrl = RiggedTimeManagerControl(iface)
        self.ctrl.initGui(test=True)
        self.tlm = self.ctrl.getTimeLayerManager()
        uri = QgsDataSourceURI()
        uri.setConnection('localhost', '5432', DBNAME, "postgres", "postgres")
        uri.setDataSource('public', TABLE, GEOMETRY_COL, '')
        self.layer =  QgsVectorLayer(uri.uri(), TABLE, 'postgres')
        self.assertTrue(self.layer.isValid())
        self.assertEquals(self.layer.featureCount(),5)

    def test_integers(self):
        self._test_layer(EPOCH_COL,timevectorlayer.DateTypes.IntegerTimestamps, time_util.UTC)

    def test_date_str(self):
        self._test_layer(DATE_STR_COL,timevectorlayer.DateTypes.DatesAsStrings, CUSTOM_FORMAT)

    def test_date_str_dmy(self):
        """Test that everything works properly with date formats that can't be compared correctly
        using their string representations"""
        start_dt=time_util.epoch_to_datetime(STARTTIME)
        end_dt=time_util.epoch_to_datetime(STARTTIME+1)
        self.assertTrue(start_dt<end_dt and datetime_to_str(start_dt,
                                                            CUSTOM_FORMAT_DMY)>datetime_to_str(end_dt,CUSTOM_FORMAT_DMY))
        self._test_layer(DATE_STR_COL_DMY,timevectorlayer.DateTypes.DatesAsStrings, CUSTOM_FORMAT_DMY)

    def test_date(self):
        self._test_layer(DATE_COL,timevectorlayer.DateTypes.DatesAsStrings, time_util.DEFAULT_FORMAT)

    @raises(Exception)
    def test_to_from_are_different_types(self):
        # currently not supported, verify that exception is thrown
         self._test_layer(DATE_COL,timevectorlayer.DateTypes.DatesAsStrings,
                          time_util.DEFAULT_FORMAT,attr2=DATE_STR_COL_DMY)

    #TODO: Issue  https://github.com/anitagraser/TimeManager/issues/33
    # Timezones not supported yet
    def test_date_with_timezone(self):
        with self.assertRaises(time_util.UnsupportedFormatException):
            self._test_layer(DATE_TZ_COL,timevectorlayer.DateTypes.DatesAsStrings, None)

    def _test_layer(self, attr, typ, tf, attr2=None):
        if attr2 is None:
            attr2=attr
        timeLayer = timevectorlayer.TimeVectorLayer(self.layer,attr,attr2,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.tlm.registerTimeLayer(timeLayer)

        self.assertEquals(timeLayer.getDateType(), typ)
        self.assertEquals(timeLayer.getTimeFormat(), tf)
        expected_datetime = time_util.epoch_to_datetime(STARTTIME)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.setTimeFrameType("seconds")
        self.assertEquals(self.layer.featureCount(),1)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.stepForward()
        self.assertEquals(self.layer.featureCount(),1)
        expected_datetime = time_util.epoch_to_datetime(STARTTIME+1)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)

if __name__=="__main__":
    unittest.main()
