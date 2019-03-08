from __future__ import absolute_import
from timemanager.interpolation.linearpointinterpolator import LinearPointInterpolatorWithQuery, LinearPointInterpolatorWithMemory # add all new interpolator classes here
from timemanager import conf


def get_interpolator_from_text(text):
    try:
        class_name = conf.INTERPOLATION_MODE_TO_CLASS[text]
    except:
        raise Exception("{} is not a valid interpolator name")
    constructor = globals()[class_name]
    return constructor()

