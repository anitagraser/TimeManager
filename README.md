# Welcome to TimeManager!

A plugin for QGIS by Anita Graser and Karolina Alexiou (aka carolinux)

* project home and bug tracker: https://github.com/anitagraser/TimeManager
* plugin repository: http://plugins.qgis.org/plugins/timemanager/

Latest news will be published on Anita's blog: http://anitagraser.com/tag/time-manager/

## What is the goal

The aim of '''Time Manager plugin for QGIS''' is to provide comfortable browsing through temporal geodata. A dock widget provides a time slider and a configuration dialog for your layers to manage.

## Newest features

As of version 1.6.0 TimeManager provides support for linear interpolation between point geometries. Please try it out and give feedback.

## What Time Manager currently does

Time Manager filters your datasets and displays only features with timestamps in the user specified time frame. Timestamps have to be in one of the following formats:

* Integer timestamp in seconds after or before the epoch (1970-1-1) 
* %Y-%m-%d %H:%M:%S.%f
* %Y-%m-%d %H:%M:%S
* %Y-%m-%d %H:%M
* %Y-%m-%dT%H:%M:%S
* %Y-%m-%d
* %Y/%m/%d %H:%M:%S.%f
* %Y/%m/%d %H:%M:%S
* %Y/%m/%d %H:%M
* %Y/%m/%d
* %H:%M:%S
* %H:%M:%S.%f
* %Y.%m.%d %H:%M:%S.%f
* %Y.%m.%d %H:%M:%S
* %Y.%m.%d %H:%M
* %Y.%m.%d

Other formats can be added by appending to the YMD_SUPPORTED_FORMATS  list in `time_util.py` a format that puts the day, the month and the year in this order. Variants that put the month or date first will be then generated automatically. We currently do not support formats that would put the minutes or seconds before the hour. Please note that the %f directive is not supported in all operating systems, because of underlying library limitations.

## Start and end time

Users of the plugin can define a start and (optionally) an end time field that describes the geometries of the layer. If only start time is defined, the plugin will select only the features that have a timestamp within the current time interval (current time until current time + time step). If an end time field is defined, then the features whose [startTime-endTime] period overlaps with the [current time, current time+time step] interval are shown. Intuitively, if we have a dataset of buildings and the dates they were built (startTime) and demolished (endTime), with TimeManager we are able to show the state of the village at any point in time. If you want to have a kind of cumulative animation where the shown points do not disappear, an often used trick is to create an artificial endTime field which is sufficiently far in the future.

## Shortcuts

Use Ctrl+Space (or Command+Space) if you are using a Mac to focus on the time slider. The left and right arrows can then move the slider.

## Supported Layer Types

TimeManager has been tested with PostgreSQL layers, Spatialite layers, delimited text layers, and .shp shapefiles. If you find that a layer of the types mentioned above doesn't behave correctly, please file a bug. If you want us to support new formats, file a feature request.

The biggest tested dataset was a Spatialite table with indexed timestamps containing approximately 400,000 points, covering a time span of 24 hours. Stepping through the data for example in 1-hour-sized steps works without problems.

## Animation

Time Manager supports exporting image series based on the defined animation settings. Our goal for future versions is to include a tool that creates actual animations from these image series. Until then, external programs can be used for this last step. See VideoTutorial.md for instructions on how to create a video from the images.

### Examples

[![IMAGE ALT TEXT HERE](http://img.youtube.com/vi/p9MPbvbpu6E/0.jpg)](http://www.youtube.com/watch?v=p9MPbvbpu6E)

[![IMAGE ALT TEXT HERE](http://img.youtube.com/vi/ax_jzqJTjgc/0.jpg)](http://www.youtube.com/watch?v=ax_jzqJTjgc)

## Limitations

The plug-in uses Python's datetime module and QDateTime for calculations. It is therefore limited to these modules' functionality. This enfolds (not exhaustive):

* Dates must be according to the formats mentioned above
* Dates must be according to the Gregorian calendar
* We fully support years from 100 AD to 8000 in the future
* Time step can be as small as one second (smaller timesteps not fully supported yet). Millisecond steps work well, but to avoid problems your dataset should have a timeformat that itself includes milliseconds, even if that means adding a trailing .0 to your time stamps. Microseconds also work, but QDateTime limitations prevent it from displaying correctly always.

We currently don't support:

* Dates with time zone notion
* Shapefiles can't be edited directly, while time-managed. This is an OGR limitation. It also exists for any other query you set: You simply can't edit a shapefile whilst a query is set.

For other known issues check https://github.com/anitagraser/TimeManager/issues?direction=desc&sort=updated&state=open

## License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Download

Time Manager is available through QGIS Plugin Repository http://plugins.qgis.org/plugins/timemanager/

## Dependencies

Time Manager 1.0 reqires **QGIS 2.0** with Python 2.7.

Other plugin dependencies: Python module dateutil (included e.g. in matplotlib available in OSGeo4W)

If you are running an **older version of QGIS**, Time Manager versions <= 0.7 require QGIS 1.7 or 1.8 with Python 2.7.

