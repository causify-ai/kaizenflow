#!/bin/bash -xe
ps -ef | grep ganache
kill $(ps -ef | grep ganache | grep node | awk '{print $2}' )
ps -ef | grep ganache
