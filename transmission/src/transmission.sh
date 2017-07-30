#!/bin/sh

RPC_PORT=9091
STORAGE_DEVICE="/media/hdd"
USER="root" 
PASSWORD="root"

NAME="transmission-daemon"
DAEMON="nice -n 19 /usr/bin/transmission-daemon"
DIRECTORY="$STORAGE_DEVICE/transmission"
DOWNLOAD_DIR="$STORAGE_DEVICE/transmission/download"
CONFIG_DIR="$STORAGE_DEVICE/transmission/config"
WATCH_DIR="$STORAGE_DEVICE/transmission/watch"
ARGS="-c $WATCH_DIR -g $CONFIG_DIR -a *.*.*.* -w $DOWNLOAD_DIR -p $RPC_PORT -t -u $USER -v $PASSWORD"
INET_ADDR=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
PATH=/usr/sbin:/usr/bin:/sbin:/bin

if [ ! -d $STORAGE_DEVICE ] ; then
	echo "Don't activate transmission!"
	echo "No mount device for $STORAGE_DEVICE!"
	exit 1
fi

if [ ! -d $DIRECTORY ] ; then mkdir $DIRECTORY; fi
if [ ! -d $DOWNLOAD_DIR ] ; then mkdir $DOWNLOAD_DIR; fi
if [ ! -d $CONFIG_DIR ] ; then mkdir $CONFIG_DIR; fi

if [ ! -d $WATCH_DIR ] ; then
	mkdir $WATCH_DIR
 else
	rm -f $WATCH_DIR/*.added
fi

case $1 in
	start)
		if [ -n "`pidof transmission-daemon`" ] ; then
			echo "transmission is already running!"
			exit 1
		else
			echo "starting $NAME..."
			start-stop-daemon -S -b -n $NAME -a $DAEMON -- $ARGS
		fi
		sleep 3
		echo "**********************************************\n"
		if [ -n "`pidof transmission-daemon`" ] ; then
			echo "transmission activated successfully!"
			echo "Open your browser at http://$INET_ADDR:$RPC_PORT"
			if [ -e /usr/bin/trans_queue.sh ] ; then
				echo "Activated auto queue downloads..."
				chmod 755 /usr/bin/trans_queue.sh
				start-stop-daemon -S -b -x /usr/bin/trans_queue.sh &
			fi
			if [ -e /usr/bin/trans_swap.sh ] ; then
				chmod 755 /usr/bin/trans_swap.sh
				/usr/bin/trans_swap.sh start
			fi
		else
			echo "Error starting transmission!"
			/usr/bin/transmission-daemon > /tmp/errorTransmission.log
			if [ -z /tmp/errorTransmission.log ] ; then
				echo "**********************************************\n"
				cat /tmp/errorTransmission.log
				echo "**********************************************\n"
				echo "Error info write /tmp/errorTransmission.log!"
			fi
			exit 1
		fi
		echo "**********************************************\n"
	;;
	stop)
		killall trans_queue.sh > /dev/null 2>&1
		if [ -n "`pidof transmission-daemon`" ] ; then
			if [ -e /usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_start_stop_down.sh ] ; then
				chmod 755 /usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_start_stop_down.sh
				/usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_start_stop_down.sh trans_stop_down
				sleep 6
			fi
			echo -n "Stopping $NAME..."
			killall $NAME
			sleep 2
			if [ -e /usr/bin/trans_swap.sh ] ; then
				/usr/bin/trans_swap.sh stop
			fi
			echo "Done."
		else
			echo "transmission-daemon not running..."
		fi
	;;
	restart)
		echo -n "Restarting $NAME..."
		$0 stop
		sleep 10
		$0 start
	;;
	enable)
		update-rc.d transmission.sh defaults 60 
	;;
	disable)
		update-rc.d -f transmission.sh remove
		sleep 2
	;;
	*)
	echo " "
	echo "Options: $0 {start|restart|stop|enable|disable}"
	echo " "
esac

exit 0
