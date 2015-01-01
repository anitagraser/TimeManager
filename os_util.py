import platform

LINUX="linux"
MACOS="macos"
WINDOWS="windows"


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