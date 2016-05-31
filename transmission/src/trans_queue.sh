#!/bin/sh

while true
do sleep 280;

if [ -e /tmp/torrent.txt ] ; then
	CH=`cat /tmp/torrent.txt`
	if [ "$CH" = "1" ] ; then
		echo 2 > /tmp/torrent.txt
	else
		rm -rf /tmp/torrent.txt
	fi
fi

REMOTE="/usr/bin/transmission-remote"
USERNAME="root"
PASSWORD="root"
MAXDOWN="2"
MAXACTIVE="5"
CMD="$REMOTE --auth $USERNAME:$PASSWORD"

DOWNACTIVE="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | wc -l)"
if [ $MAXDOWN -lt $DOWNACTIVE ]; then
	DOWNTOSTOP="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | \
		tail -n $(expr $DOWNACTIVE - $MAXDOWN) | awk '{ print $1; }')"
	for ID in $DOWNTOSTOP; do
		NAME="$($CMD --torrent $ID --info | grep Name:)"
		$CMD --torrent $ID --stop >> /dev/null 2>&1
	done
else
	[ $(expr $MAXDOWN - $DOWNACTIVE) -gt 0 ] && (
	DOWNINACTIVE="$($CMD -l | tail +2 | grep -v 100% | grep Stopped | wc -l)"
	[ $DOWNINACTIVE -gt 0 ] && (
		DOWNTOSTART="$($CMD -l | tail +2 | grep -v 100% | grep Stopped | \
			head -n $(expr $MAXDOWN - $DOWNACTIVE) | awk '{ print $1; }')"
		for ID in $DOWNTOSTART; do
			NAME="$($CMD --torrent $ID --info | grep Name:)"
			$CMD --torrent $ID --start > /dev/null 2>&1
			echo 1 > /tmp/torrent.txt
		done
		)
	)
fi

sleep 20

if [ -e /tmp/torrent.txt ] ; then
	echo " "
else
	if [ -e /usr/bin/trans_stop.sh ] ; then
		/usr/bin/trans_stop.sh
	fi
fi

done
