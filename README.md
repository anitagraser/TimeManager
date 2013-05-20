# Welcome to TimeManager!

A plugin for QGIS by Anita Graser 

* project home and bug tracker: https://github.com/anitagraser/TimeManager
* plugin repository: http://plugins.qgis.org/plugins/plugins.xml

Latest news will be published on my blog: http://anitagraser.com/tag/time-manager/


## What is the goal

The aim of '''Time Manager plugin for QGIS''' is to provide comfortable browsing through temporal geodata. A dock widget provides a time slider and a configuration dialog for your layers to manage.

## What Time Manager currently does

Time Manager filters your datasets and displays only features with timestamps in the user specified time frame. Timestamps have to be in one of the following formats:

* YYYY-MM-DD HH:MM:SS.ssssss
* YYYY-MM-DD HH:MM:SS
* YYYY-MM-DD HH:MM
* YYYY-MM-DD
* YYYY/MM/DD HH:MM:SS

Other formats can be added by appending to the `supportedFormats` list in `timelayer.py`.

The biggest tested dataset was a Spatialite table with indexed timestamps containing approximately 400,000 points, covering a time span of 24 hours. Stepping through the data for example in 1-hour-sized steps works without problems.

Time Manager 0.3 supports exporting image series based on the defined animation settings. Our goal for future versions is to include a tool that creates actual animations from these image series. Until then, external programs can be used for this last step. A good option is memcoder. This is how it's used to create an .avi from all images within a folder:

``mencoder "mf://*.PNG" -mf fps=10 -o output.avi -ovc lavc -lavcopts vcodec=mpeg4``

## License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Dependencies

The latest version of Time Manager requries QGIS >= 1.9 with Python 2.7.

Time Manager versions <= 0.7 require QGIS 1.7 or 1.8 with Python 2.7.

other plugin dependencies: Python module dateutil (included e.g. in matplotlib available in OSGeo4W)

## What are the limitations?

The plug-in uses Python's datetime module for calculations. It is therefore limited to the module's functionality. This enfolds (not exhaustive):

* Dates must be according to the format mentioned above
* Dates must accord to the Gregorian calendar
* **The range of years is limited**. The exact range of manageable years is dependent on your platform. This is due to limitations in time.mktime. (Problems have been reported with dates before 1970.)
* Limits to the size/resolution of the time frame size

We currently don't support:

* Leap years
* Dates with time zone notion
* Shapefiles can't be edited directly, while time-managed. This is an OGR limitation. It also exists for any other query you set: You simply can't edit a shapefile whilst a query is set.

Please review the tickets for more information!

### Other limitations

Shapefiles can't be edited directly, while time-managed. This is an OGR limitation. It also exists for any other query you set: You simply can't edit a shapefile whilst a query is set.

It is not possible to time-manage Delimited Text layers. This is a limitation of the data provider. Save the data as e.g. Shapefile to use it with Time Manager.

## Where to download Time Manager

Time Manager is available through QGIS Plugin Repository http://plugins.qgis.org/plugins/timemanager/
