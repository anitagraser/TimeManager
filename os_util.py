import platform

LINUX="linux"
MACOS="macos"
WINDOWS="windows"

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


def get_os():
    """Determine OS"""
    # details of platform implementation
    # https://hg.python.org/cpython/file/2.7/Lib/platform.py#l1568
    if "linux" in platform.platform().lower():
        return LINUX
    elif "macos" in platform.platform().lower():
        return MACOS
    elif "windows" in platform.platform().lower():
        return WINDOWS
    else:
        raise Exception("OS not found")

#TODO figure out possible prefix paths for Mac & Windows
#TODO Make it possible to test against a list of paths (Qt + unittest has some issues)
os_prefix_paths={LINUX:"/usr", MACOS:None, WINDOWS:None}

def get_possible_prefix_path():
    return os_prefix_paths[get_os()]