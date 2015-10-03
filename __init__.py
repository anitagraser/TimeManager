# -*- coding: UTF-8 -*-


def classFactory(iface):
    from timemanager import timemanager

    return timemanager(iface)
