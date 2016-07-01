from interpolator import *
from queryinterpolator import *

from ..tmlogging import warn


class LinearPointInterpolator(Interpolator):
    def getGeometryFromFeature(self, feat):
        geom = feat.geometry()
        if geom.type() != QGis.Point:
            warn("Ignoring 1 non-point geometry")
            return None
        coords = (geom.asPoint().x(), geom.asPoint().y())
        return coords

    def interpolate(self, Tvalue, Tvalues, Gvalues):
        warn("{}, inbetween {}".format(Tvalue, Tvalues))
        xpos1, ypos1 = Gvalues[0]
        xpos2, ypos2 = Gvalues[1]
        # Interpolate
        x_pos = [xpos1, xpos2]
        y_pos = [ypos1, ypos2]
        interp_x = np.interp(Tvalue, Tvalues, x_pos)
        interp_y = np.interp(Tvalue, Tvalues, y_pos)
        # info(str(interp_x)+" "+str(interp_y))
        return [interp_x, interp_y]


class LinearPointInterpolatorWithMemory(MemoryLoadInterpolator, LinearPointInterpolator):
    pass


class LinearPointInterpolatorWithQuery(QueryInterpolator, LinearPointInterpolator):
    pass
