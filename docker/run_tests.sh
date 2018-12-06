#!/bin/bash
cd /usr
cp -r src TimeManager
xvfb-run nosetests TimeManager --cover-package=TimeManager 
rc=$?
exit $rc
