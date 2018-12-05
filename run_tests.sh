#!/bin/bash
find -name '*.pyc' -delete
nosetests --cover-package=TimeManager 
rc=$?
exit $rc
