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

case "$1" in
	pause)
		MAXDOWN="0"
		DOWNACTIVE="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | wc -l)"
		if  [ $MAXDOWN -lt $DOWNACTIVE ]; then
			DOWNTOSTOP="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | \
			tail -n $(expr $DOWNACTIVE - $MAXDOWN) | awk '{ print $1; }')"
			for ID in $DOWNTOSTOP; do
				NAME="$($CMD --torrent $ID --info | grep Name:)"
				$CMD --torrent $ID --stop > /dev/null 2>&1
			done
		fi
		killall trans_queue.sh > /dev/null 2>&1
		echo "**********************************************\n"
		echo "All current downloads placed on pause..."
		echo "**********************************************\n"
	;;
	unpause)
		MAXDOWN="50"
		DOWNACTIVE="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | wc -l)"
		if [ $MAXDOWN -lt $DOWNACTIVE ]; then
			DOWNTOSTOP="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | \
			tail -n $(expr $DOWNACTIVE - $MAXDOWN) | awk '{ print $1; }')"
			for ID in $DOWNTOSTOP; do
				NAME="$($CMD --torrent $ID --info | grep Name:)"
				$CMD --torrent $ID --stop > /dev/null 2>&1
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
				done
				)
			)
		fi
		echo "**********************************************\n"
		echo "All current downloads are running..."
		echo "**********************************************\n"
	;;
	trans_stop_down)
		MAXDOWN="0"
		DOWNACTIVE="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | wc -l)"
		if [ $MAXDOWN -lt $DOWNACTIVE ]; then
			DOWNTOSTOP="$($CMD -l | tail +2 | grep -v 100% | grep -v Sum | grep -v Stopped | \
			tail -n $(expr $DOWNACTIVE - $MAXDOWN) | awk '{ print $1; }')"
			for ID in $DOWNTOSTOP; do
				NAME="$($CMD --torrent $ID --info | grep Name:)"
				$CMD --torrent $ID --stop > /dev/null 2>&1
			done
		fi
	;;
	trans_stop)
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
	;;
	*)
	echo "Usage: $0 pause|unpause|trans_stop|trans_stop_down"
	exit 1
	;;
esac
exit 0
