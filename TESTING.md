# Testing

We test the local deployment using Docker/docker-compose and we use the same Dockerized setup with Travis CI. You need to have Docker and docker-compose>=1.13.0 installed.

Before pushing your local commits to github, run the tests locally, from the toplevel directory of the repo:

```
sh docker/run_tests_local.sh
```


