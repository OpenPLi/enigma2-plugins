#!/bin/sh

if [ -n "`pidof transmission-daemon`" ] ; then
	echo " "
else 
	echo "transmission-daemon not running..."
	exit 1
fi
REMOTE="/usr/bin/transmission-remote"
USERNAME="root"
PASSWORD="root"
CMD="$REMOTE --auth $USERNAME:$PASSWORD"
$CMD -l > /tmp/info_trans.txt
TEST=`cat /tmp/info_trans.txt`
if [ -n "$TEST" ] ; then
	DOWNACTIVE="$(cat /tmp/info_trans.txt | head -n 20 | grep  'Downloading' | wc -l)"
	if [ $DOWNACTIVE = 0 ]; then
		IDLEACTIVE="$(cat /tmp/info_trans.txt  | head -n 20 | grep -v '100%' | grep  'Idle'  | wc -l)"
		if [ $IDLEACTIVE = 0 ]; then
			VERACTIVE="$(cat /tmp/info_trans.txt | head -n 20 | grep  'Verifying'  | wc -l)"
			if [ $VERACTIVE = 0 ]; then
				UPACTIVE="$(cat /tmp/info_trans.txt | head -n 20 | grep -v '100%' | grep  'Up & Down'   | wc -l)"
				if [ $UPACTIVE = 0 ]; then 
					echo "**********************************************\n" >>/tmp/info_trans.txt  
					date >>/tmp/info_trans.txt
					echo "**********************************************\n" >>/tmp/info_trans.txt
					echo "Latest information on stopping transmission-daemon" >>/tmp/info_trans.txt 
					echo "**********************************************\n" >>/tmp/info_trans.txt
					/etc/init.d/transmissiond stop > /dev/null 2>&1
				fi
			fi
		fi
	fi
fi

exit 0

