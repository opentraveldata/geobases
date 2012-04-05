#!/bin/bash


echo
echo 'ps aux'
echo '------'
ps aux |grep -E 'Webservice'|grep -v 'grep' 

echo
echo 'killing'
echo '-------'
ps aux |grep -E 'Webservice'|grep -v 'grep' |awk '{print $2}' |xargs kill -9

echo
echo 'ps aux'
echo '------'
ps aux |grep -E 'Webservice'|grep -v 'grep'
