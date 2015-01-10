# Welcome to TimeManager!

A plugin for QGIS by Anita Graser 

* project home and bug tracker: https://github.com/anitagraser/TimeManager
* plugin repository: http://plugins.qgis.org/plugins/timemanager/

Latest news will be published on my blog: http://anitagraser.com/tag/time-manager/


## What is the goal

The aim of '''Time Manager plugin for QGIS''' is to provide comfortable browsing through temporal geodata. A dock widget provides a time slider and a configuration dialog for your layers to manage.

## What Time Manager currently does

Time Manager filters your datasets and displays only features with timestamps in the user specified time frame. Timestamps have to be in one of the following formats:

* Integer timestamp in seconds after or before the epoch (1970-1-1) 
* YYYY-MM-DD HH:MM:SS.ssssss
* YYYY-MM-DD HH:MM:SS
* YYYY-MM-DD HH:MM
* YYYY-MM-DD
* YYYY/MM/DD HH:MM:SS.ssssss
* YYYY/MM/DD HH:MM:SS
* YYYY/MM/DD HH:MM
* YYYY/MM/DD
* DD.MM.YYYY HH:MM:SS.ssssss
* DD.MM.YYYY HH:MM:SS
* DD.MM.YYYY HH:MM
* DD.MM.YYYY
* DD-MM-YYYY HH:MM:SS.ssssss
* DD-MM-YYYY HH:MM:SS
* DD-MM-YYYY HH:MM
* DD-MM-YYYY
* DD/MM/YYYY HH:MM:SS.ssssss
* DD/MM/YYYY HH:MM:SS
* DD/MM/YYYY HH:MM
* DD/MM/YYYY

Other formats can be added by appending to the `supportedFormats` list in `timevectorlayer.py`.

The biggest tested dataset was a Spatialite table with indexed timestamps containing approximately 400,000 points, covering a time span of 24 hours. Stepping through the data for example in 1-hour-sized steps works without problems.

Time Manager supports exporting image series based on the defined animation settings. Our goal for future versions is to include a tool that creates actual animations from these image series. Until then, external programs can be used for this last step. A good option is memcoder. This is how it's used to create an .avi from all images within a folder:

``mencoder "mf://*.png" -mf fps=10 -o output.avi -ovc lavc -lavcopts vcodec=mpeg4``

## License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Dependencies

Time Manager 1.0 reqires **QGIS 2.0** with Python 2.7.

Other plugin dependencies: Python module dateutil (included e.g. in matplotlib available in OSGeo4W)

If you are running an **older version of QGIS**, Time Manager versions <= 0.7 require QGIS 1.7 or 1.8 with Python 2.7.

## What are the limitations?

The plug-in uses Python's datetime module for calculations. It is therefore limited to the module's functionality. This enfolds (not exhaustive):

* Dates must be according to the formats mentioned above
* Dates must accord to the Gregorian calendar
* We fully support years from 100 AD to 8000 in the future, however the number of seconds between the first timestamp and the last timestamp needs to fit in an integer. This is over 2 billion seconds, so most use cases should be fine.
* Limits to the size/resolution of the time frame size

We currently don't support:

* Leap years
* Dates with time zone notion
* Shapefiles can't be edited directly, while time-managed. This is an OGR limitation. It also exists for any other query you set: You simply can't edit a shapefile whilst a query is set.

Please review the tickets for more information!

### Other limitations

Shapefiles can't be edited directly, while time-managed. This is an OGR limitation. It also exists for any other query you set: You simply can't edit a shapefile whilst a query is set.

It is not possible to time-manage Delimited Text layers. This is a limitation of the data provider. Save the data as e.g. Shapefile to use it with Time Manager.

For other known issues check https://github.com/anitagraser/TimeManager/issues?direction=desc&sort=updated&state=open

## Where to download Time Manager

Time Manager is available through QGIS Plugin Repository http://plugins.qgis.org/plugins/timemanager/

## Testing

If you want to contribute, please test your changes. We are using the unittest  framework. If you have nose, mock, pyqt4 and qgis.core  installed in Python, you can run run_tests.sh to see a report about test success and code coverage. Before finalizing a pull request, you are also advised to test manually that the testdata/tweets.shp shapefile loads correctly and exports as a number of frames, for years 1965 and 1165.

TODO: Better instructions for installing the test dependencies, Travis continuous testing setup
