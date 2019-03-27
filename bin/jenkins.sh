#!/bin/bash

set -e  # exit on errors
set -x  # echo commands

if [[ -z "$WORKSPACE" ]]; then
    export WORKSPACE=$(pwd)
fi

docker stop gemma-zaaktypecatalogus-pr-tests_db_1
docker stop gemma-zaaktypecatalogus-stable_db_1
docker stop gemma-zaaktypecatalogus-develop_db_1

exit 1



# # use the Jenkins specific override
# cp bin/docker-compose.override.yml docker-compose.override.yml

# docker-compose build tests
# docker-compose run tests

# # cleanup
# git reset --hard
