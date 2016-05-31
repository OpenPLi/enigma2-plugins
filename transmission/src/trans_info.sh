#!/bin/sh

if [ -n "`pidof transmission-daemon`" ] ; then
	echo "**********************************************\n"
	echo "Transmission-daemon running!\n"
	echo "**********************************************\n"
	REMOTE="/usr/bin/transmission-remote"
	USERNAME="root"
	PASSWORD="root"
	IMD="$REMOTE --auth $USERNAME:$PASSWORD"
	$IMD -l > /tmp/transmission.tmp
	echo "**********************************************\n" >> /tmp/transmission.tmp
	echo `cat /tmp/transmission.tmp |  awk '/Downloading/ { print $1}'` >/tmp/Downloading.list

	DWA=`sed -n '1 { s/ .*$//; p }' /tmp/Downloading.list`
	echo $DWA > /tmp/Downl.list
	DWAA=`cat /tmp/Downl.list`
	if [  -n "$DWAA" ] ; then
		$IMD -t $DWA -i | sed -n '1,22p' >> /tmp/transmission.tmp 
		echo "**********************************************\n" >> /tmp/transmission.tmp
	fi

	DWB=`read N1 N2   < /tmp/Downloading.list; echo "$N2 "`
	echo $DWB > /tmp/Downl1.list
	DWBB=`cat /tmp/Downl1.list`

	if [ -n "$DWBB" ] ; then
		$IMD -t $DWB -i | sed -n '1,22p' >> /tmp/transmission.tmp 
		echo "**********************************************\n" >> /tmp/transmission.tmp
	fi

	cat /tmp/transmission.tmp
	rm /tmp/transmission.tmp > /dev/null 2>&1
	rm /tmp/Downl.list > /dev/null 2>&1
	rm /tmp/Downl1.list > /dev/null 2>&1
	rm /tmp/Downloading.list > /dev/null 2>&1
else
	echo "**********************************************\n"
	echo "Transmission-daemon not running!"
	echo "**********************************************\n"
	if [ -e /tmp/info_trans.txt ] ; then   
		cat /tmp/info_trans.txt
	fi 
fi

exit 0
