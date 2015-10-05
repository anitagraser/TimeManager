__author__ = 'carolinux'

import unittest

from TimeManager import layer_settings


INTERP_SAVESTRING = "timespans20150228135607432;;ARRIVAL;ARRIVAL;True;%Y-%m-%d %H:%M:%S;0;;True"
NOINTERP_SAVESTRING = "tweets20150228140256944;;T;T;True;%Y-%m-%d %H:%M:%S;0;;False"


class TestLayerSettings(unittest.TestCase):
    def test_import_savestring(self):
        ls = layer_settings.getSettingsFromSaveStr(INTERP_SAVESTRING)
        assert (ls.interpolationEnabled)
        ls = layer_settings.getSettingsFromSaveStr(NOINTERP_SAVESTRING)
        assert (not ls.interpolationEnabled)