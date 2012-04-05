#!/bin/bash

cd `dirname $0`

#nohup /usr/bin/python ./Webservice.py > /dev/null 2>&1 & 
nohup /usr/bin/python ./WebserviceOverTornado.py > /dev/null 2>&1 & 

# Test
#time curl -s "http://localhost:14003/airports/ORY?[1-10000]" > /dev/null
