from linearpointinterpolator import LinearPointInterpolatorWithQuery, LinearPointInterpolatorWithMemory # add all new interpolator classes here
from .. import conf as conf


def get_interpolator_from_text(text):
    try:
        class_name = conf.INTERPOLATION_MODE_TO_CLASS[text]
    except:
        raise Exception("{} is not a valid interpolator name")
    constructor = globals()[class_name]
    return constructor()

