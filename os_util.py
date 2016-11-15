import platform
import os

LINUX = "linux"
MACOS = "macos"
WINDOWS = "windows"

__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


def get_os():  # pragma: no cover
    """Determine OS"""
    # details of platform implementation
    # https://hg.python.org/cpython/file/2.7/Lib/platform.py#l1568
    if "linux" in platform.platform().lower():
        return LINUX
    elif "macos" or "darwin" in platform.platform().lower():
        return MACOS
    elif "windows" in platform.platform().lower():
        return WINDOWS
    else:
        raise Exception("OS not found")

# TODO have people confirm the prefix path for Mac
# TODO Make it possible to test against a list of paths
# (Qt + unittest has some issues when looping over paths and re-initializing, unfortunately)
os_prefix_paths = {LINUX: "/usr", MACOS: "/Applications/QGIS.app/Contents",
                   WINDOWS: "C:/PROGRA~1/QGISBR~1/apps/qgis"}


def get_possible_prefix_path():  # pragma: no cover
     # ideally the dev environment has set a "QGIS_PREFIX_PATH"
    if os.getenv("QGIS_PREFIX_PATH", None) is not None:
        return os.getenv("QGIS_PREFIX_PATH")
    elif os.getenv("PREFIX_PATH", None) is not None:
        return os.getenv("PREFIX_PATH")
    else:  # raw guessing
        return os_prefix_paths[get_os()]
