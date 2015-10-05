from datetime import datetime, timedelta
import unittest

import TimeManager.raster.cdflayer as cdf
import TimeManager.time_util as time_util


class TestCDFRasterLayer(unittest.TestCase):
    def setUp(self):
        self.dts = [datetime(2014, 1, 1), datetime(2014, 1, 2), datetime(2014, 1, 4),
                    datetime(2014, 1, 5)]

    def test_date_extraction(self):
        epoch = 1393786800
        bandName = "Band 002 / time={} (seconds since 1970-01-01 00:00:00)".format(epoch)
        self.assertEqual(cdf.CDFRasterLayer.extract_time_from_bandname(bandName),
                         time_util.epoch_to_datetime(epoch))


    def test_get_first_band_between(self):
        # when it's at the start
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts, self.dts[0], self.dts[1])
        self.assertEqual(bandNo, 1)  # the first band
        # when it's in between
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts, self.dts[1],
                                                           self.dts[1] + timedelta(hours=6))
        self.assertEqual(bandNo, 2)  # the second band
        # when it's at the end
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts,
                                                           self.dts[1] + timedelta(hours=3),
                                                           self.dts[2])
        self.assertEqual(bandNo, 2)  # the second band
        # when it's at after the end
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts,
                                                           self.dts[1] + timedelta(hours=3),
                                                           self.dts[2] + timedelta(hours=1))
        self.assertEqual(bandNo, 3)  # the second band
        # when it's after the end
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts,
                                                           self.dts[-1] + timedelta(hours=6),
                                                           self.dts[-1] + timedelta(hours=12))
        self.assertEqual(bandNo, len(self.dts))  # the last band
        # when it's before the beginning
        bandNo = cdf.CDFRasterLayer.get_first_band_between(self.dts,
                                                           self.dts[0] - timedelta(hours=6),
                                                           self.dts[0] - timedelta(hours=2))
        self.assertEqual(bandNo, 1)  # the first band

