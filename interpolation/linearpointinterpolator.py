from interpolator import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class LinearPointInterpolator(MemoryLoadInterpolator):

    def getGeometryFromFeature(self,feat):
        geom = feat.geometry()
        if geom.type()!=QGis.Point:
            QgsMessageLog.logMessage("Ignoring 1 non-point geometry")
            return None
        coords = (geom.asPoint().x(), geom.asPoint().y())
        return coords

    def interpolate(self, Tvalue, Tvalues, Gvalues):
        xpos1,ypos1 = Gvalues[0] 
        xpos2,ypos2 = Gvalues[1] 
        # Interpolate
        x_pos = [xpos1, xpos2]
        y_pos = [ypos1, ypos2]
        interp_x = np.interp(Tvalue,Tvalues,x_pos)
        interp_y = np.interp(Tvalue,Tvalues,y_pos)
        QgsMessageLog.logMessage(str(interp_x)+" "+str(interp_y))
        return [interp_x, interp_y]
