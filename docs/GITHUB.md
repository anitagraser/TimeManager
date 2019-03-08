## How do I check out a fixed version from Github?

Some times people report issues on Github which get fixed
on Github, but are not yet part of an official release of
Time Manager. In order to get the most recent master you need
to go to the QGIS plugin directory on your computer:

```
~/.qgis2/python/plugins # for Linux and Mac
C:\Users\{username}\.qgis2\plugins\python # for Windows
```

You need to delete the directory "TimeManager" from there and
then and run, from this directory:

```
git clone https://github.com/anitagraser/TimeManager.git 
```

This will replace the current version of the plugin downloaded from
the QGIS plugins repository with the current version from github. For this,
you need to have Git installed.

If you want to update the plugin again, go to the QGIS plugin directory,
go into the TimeManager directory and type:
 
```
git pull
```

