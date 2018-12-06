export QGIS_TEST_VERSION='latest'
export TRAVIS_BUILD_DIR=$PWD

docker-compose -f docker/docker-compose.travis.yml run qgis bash /usr/src/docker/run_tests.sh
