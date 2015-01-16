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

Time Manager supports exporting image series based on the defined animation settings. Our goal for future versions is to include a tool that creates actual animations from these image series. Until then, external programs can be used for this last step. A good option is mencoder. This is how it's used to create an .avi from all images within a folder:

``mencoder "mf://*.png" -mf fps=10 -o output.avi -ovc lavc -lavcopts vcodec=mpeg4``

On newer Macs, mencoder may not work.  One alternative is a powerful command-line program called ffmpeg (https://www.ffmpeg.org/). There may also be more user-friendly GUI options (such as QuickTime Pro). 

A generic problem in creating a video is that the frame rate must be chosen, which affects how you choose the "time frame size" in TimeManager.  Most videos play at approximately 30 frames per second.  Slower rates are acceptable, but will look choppier.  Here is an example calculation for animating a set of animal tracks:  
  1. Number of track-hours in the data set: 10,080  
  2. Desired video length: 3 minutes (180 seconds)  
  3. If the length of the time frame size was set to 1 hour in TimeManager, the video would have 10,080 frames.  Given the desired video length of 180 seconds that would come out to 10,080/180 = 56 frames/second, which would be too fast.  Instead, creating 1 frame per 2 track-hours results in a pretty normal 35 fps frame rate. Of course, the video length could also be altered.

Example ffmpeg command to create a video from individual .png frames:
``ffmpeg -f image2 -r 35 -i frame%04d.png -vcodec libx264 -vf fps=35 -pix_fmt yuv420p out.mp4``

What the ffmpeg flags mean:
* -f force the input or output filetype
* -r (rate): frame rate (Hz)
* -i (input): input file.  frame%04d.png means the name is formatted with 4 digits, as in "frame0000.png".  Check the filename format created by TimeManager; if you only had hundreds of frames, the filename numbering format might be "frame%03d".  The files have to be organized with padded zeros; otherwise you can use a "blob" naming option 
* -vcodec video codec.  libx264: x264 is a free software library and application for encoding video streams into the H.264/MPEG-4 AVC compression format.
* -vf fps=35 video filter(vf); frames per second (fps) = 35.  A filter is a processing step in ffmpeg parlance.
* -pix_fmt yuv420p (pixel format): YUV is a color space typically used as part of a color image pipeline, and 420p refers to the image resolution
* out.mp4 name of the output file

Other potentially useful ffmpeg flags:  
* -s (size): frame size.  WxH (width x height) is the default (keep output same as input)
* -fs (file size): limit the file size (expressed in bytes)


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

##Contributing translation files

If you want to create a translation for a language
* Go to http://www.loc.gov/standards/iso639-2/php/code_list.php and find the 2-character ISO 639-1
code of the language you want to contribute for, let's say 'it' for Italian
* go to folder i18n
* create a copy of timemanager_de.ts and rename it to timemanager_it.ts
* edit the text file with your translations
* (optional) If you can install lrelease on yor system, install it and run lrelease
timemanager_it.ts to create timemanager_it.qm. Add this file to git
* Create a pull request with your translation file(s)

## Testing

If you want to contribute, please test your changes. We are using the unittest  framework. If you have nose, mock, pyqt4 and qgis.core  installed in Python, you can run run_tests.sh to see a report about test success and code coverage. Before finalizing a pull request, you are also advised to test manually that the testdata/tweets.shp shapefile loads correctly and exports as a number of frames, for years 1965 and 1165.

TODO: Better instructions for installing the test dependencies, Travis continuous testing setup
