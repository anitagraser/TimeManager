# Contributing

We welcome contribution from the community. Please review the guidelines below.

## Reporting Bugs

Please include a step by step account of how the error appeared, a sample file, your operating system, the QGIS version and the plugin version.
If you want to file a request for supporting a new time format, you are advised to also share a sample file. After version 1.6.0 Time Manager logs some helpful messages in a special tab. Go to View/Panels/Log Messages and look at the Time Manager tab. Please attach the output there in your bug report as well.

## Contributing translation files

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

If you want to contribute code, please test your changes.

If you are using Linux, you can do the following: 
```
bash run_test.sh
```
You need to have the following system packages installed:
* python-qt4
* qgis
* python-qgis

You need to have the following python packages installed:
* mock
* nose
* coverage
* psycopg2

The test environment is not very easy to set up because of some issues with the availability and compatibility of different packages, so, for that reason, we have a continuous integration system set up, so pull requests that break the tests will be detected automatically by tests that run on a virtual machine provided by Travis CI.


