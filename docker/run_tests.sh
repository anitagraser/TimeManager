#!/bin/bash
cd /usr
cp -r src TimeManager
xvfb-run nosetests TimeManager -s --cover-package=TimeManager 
rc=$?
exit $rc
