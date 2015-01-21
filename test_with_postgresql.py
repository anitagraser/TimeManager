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
from timevectorlayer import  STRINGCAST_FORMAT,INT_FORMAT
from mock import Mock

import psycopg2

DBNAME="mydb"
TABLE="pts"

GEOMETRY_COL="geom"
DATE_COL="_date"
DATE_TZ_COL="_datetz"
EPOCH_COL="epoch"
DATE_STR_COL="datestr"

STARTTIME=1421676080

SQL_STATEMENT="""
DROP TABLE IF EXISTS {};
CREATE TABLE {} (

   {} geometry,
   {} timestamp, -- date with time of day without timezone
   {} timestamp with time zone, -- has timezone in format +xx
   {} integer,
   {} text

);

insert into pts (geom,_date,_datetz, epoch,datestr) values (ST_MakePoint(1.0,1.02),NULL,NULL,{},NULL);
insert into pts (geom,_date,_datetz, epoch,datestr) values (ST_MakePoint(1.01,1.01),NULL,NULL,1421676080,NULL);
insert into pts (geom,_date,_datetz, epoch,datestr) values (ST_MakePoint(1.02,1.01),NULL,NULL,1421676081,NULL);
insert into pts (geom,_date,_datetz, epoch,datestr) values (ST_MakePoint(1.00,1.03),NULL,NULL,1421676082,NULL);
insert into pts (geom,_date,_datetz, epoch,datestr) values (ST_MakePoint(1.0,1.04),NULL,NULL,1421676083,NULL);
set timezone='UTC';
update pts set _date = to_timestamp(epoch);
update pts set datestr = to_char(_date,'YYYY/MM/DD HH24:MI:SS');
update pts set _datetz = to_timestamp(epoch);
""".format(TABLE,TABLE,GEOMETRY_COL,DATE_COL,DATE_TZ_COL,EPOCH_COL, DATE_STR_COL,STARTTIME)

CUSTOM_FORMAT="%Y/%m/%d %H:%M:%S"

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

    def test_date(self):
        self._test_layer(DATE_COL,timevectorlayer.DateTypes.DatesAsStrings, time_util.DEFAULT_FORMAT)

    #TODO: Issue  https://github.com/anitagraser/TimeManager/issues/33
    # Timezones not supported yet
    def test_date_with_timezone(self):
        with self.assertRaises(time_util.UnsupportedFormatException):
            self._test_layer(DATE_TZ_COL,timevectorlayer.DateTypes.DatesAsStrings, None)

    def _test_layer(self, attr, typ, tf):
        timeLayer = timevectorlayer.TimeVectorLayer(self.layer,attr,attr,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.tlm.registerTimeLayer(timeLayer)

        self.assertEquals(timeLayer.getDateType(), typ)
        self.assertEquals(timeLayer.getTimeFormat(), tf)
        self.tlm.setTimeFrameType("seconds")
        expected_datetime = time_util.epoch_to_datetime(STARTTIME)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.stepForward()
        expected_datetime = time_util.epoch_to_datetime(STARTTIME+1)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)

if __name__=="__main__":
    unittest.main()
