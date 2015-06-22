from qgis.core import QgsMultiBandColorRenderer 

def findLastVisibleBand(layer, start_dt, end_dt):
    """Find the last band idx that is visible within start-end"""
    p = layer.dataProvider()
    cnt = p.bandCount()
    # TODO... 
    # p.generateBandName(2)
    return 1

def changeRenderer(layer, idx):
    p = layer.dataProvider()
    newr =  QgsMultiBandColorRenderer( layer.dataProvider(), idx, idx, idx )
    oldr = layer.renderer()
    newr.redContrastEnhancement()

    newr.setRedContrastEnhancement(oldr.redContrastEnhancement())
    newr.setGreenContrastEnhancement(oldr.greenContrastEnhancement())
    newr.setBlueContrastEnhancement(oldr.blueContrastEnhancement())
    layer.setRenderer(newr)
