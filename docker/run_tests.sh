#!/bin/bash
cd /usr
cp -r src TimeManager
mv TimeManager timemanager
xvfb-run nosetests timemanager -s --cover-package=TimeManager
rc=$?
exit $rc
