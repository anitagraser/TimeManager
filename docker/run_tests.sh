#!/bin/bash
cd /usr/src/
find -name '*.pyc' -delete
nosetests --cover-package=TimeManager 
rc=$?
exit $rc
