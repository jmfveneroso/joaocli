#!/bin/bash
docker stop $(docker ps | awk '{if (NR == 2) print $1}')
