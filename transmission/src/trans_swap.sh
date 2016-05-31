#!/bin/sh 

case $1 in
	start)
		echo `cat /proc/swaps |  awk '/swapfile / { print $1}'` >/tmp/swap.list
		SWAP=`cat /tmp/swap.list`
		if [ -n "$SWAP" ] ; then
			echo "SWAP is already running"
			rm -rf /tmp/swap.list > /dev/null 2>&1
			exit 0
		else
			if [ -e /media/hdd/swapfile ] ; then
				swapon /media/hdd/swapfile > /dev/null 2>&1
				echo "Enable /media/hdd/swapfile when start transmission"
			fi
		fi
	;;
	stop)
		if [ -e /tmp/swap.list ] ; then
			if [ -e /media/hdd/swapfile ] ; then
				swapoff /media/hdd/swapfile > /dev/null 2>&1
				rm -rf /tmp/swap.list > /dev/null 2>&1
				echo "Disable /media/hdd/swapfile when stop transmission"
			fi
		fi
	;;
	enabled)
		if [ -e /usr/bin/trans_swap.sh ] ; then
			chmod 755 /usr/bin/trans_swap.sh
			echo "Activate auto enabled SWAP when transmission-daemon running..."
		else
			cp /usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_swap.sh /usr/bin/trans_swap.sh > /dev/null 2>&1
			if [ -e /usr/bin/trans_swap.sh ] ; then
				chmod 755 /usr/bin/trans_swap.sh
				echo "**********************************************\n"
				echo "Activate auto enabled SWAP when transmission-daemon running..."
				echo "**********************************************\n"
				echo "Need restart transmission-daemon!"
				echo "**********************************************\n"
			else
				echo "Not found file /usr/bin/trans_swap.sh!"
			fi
		fi
	;;
	disabled)
		if [ -e /usr/bin/trans_swap.sh ] ; then
			/usr/bin/trans_swap.sh stop
			rm -rf /usr/bin/trans_swap.sh > /dev/null 2>&1
			echo "**********************************************\n"
			echo "Deactivate auto enabled SWAP when transmission-daemon running..."
			echo "**********************************************\n"
		else
			echo "**********************************************\n"
			echo "This option not enabled earlier..."
			echo "**********************************************\n"
		fi
	;;
	create)
		if [ -d /media/hdd ] ; then
			if [ -e /media/hdd/swapfile ] ; then
				echo "Swap already was created earlier!"
			else
				echo "Creating Swap..."
				echo " "
				dd if=/dev/zero of=/media/hdd/swapfile bs=1M count=128
				mkswap /media/hdd/swapfile
				echo " "
				if [ -e /media/hdd/swapfile ] ; then
					echo "Swap created successfully!"
					echo " "
					echo "Size 128Mb"
				else
					echo "Creating Swap failed."
				fi
			fi
			else
				echo "Not found folder /media/hdd!"
		fi
	;;
	on)
		cp /usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_queue.sh /usr/bin/trans_queue.sh > /dev/null 2>&1
		if [ -e /usr/bin/trans_queue.sh ] ; then
			chmod 755 /usr/bin/trans_queue.sh
			echo "**********************************************\n"
			echo "Turn on automatic downloads queue..."
			echo "**********************************************\n"
		else
			echo "**********************************************\n"
			echo "Failed turn on automatic downloads queue..."
			echo "**********************************************\n"
		fi
	;;
	off)
		killall trans_queue.sh > /dev/null 2>&1
		rm -rf /usr/bin/trans_queue.sh > /dev/null 2>&1
		echo "**********************************************\n"
		echo "Turn off automatic downloads queue..."
		echo "**********************************************\n"
	;;
	stop_trans)
		cp /usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_stop.sh /usr/bin/trans_stop.sh > /dev/null 2>&1
		if [ -e /usr/bin/trans_stop.sh ] ; then
			chmod 755 /usr/bin/trans_stop.sh
			echo "**********************************************\n"
			echo "Enabled automatic stop transmission after downloads ..."
			echo "**********************************************\n"
		else
			echo "**********************************************\n"
			echo "Failed enabled automatic stop transmission after downloads ..."
			echo "**********************************************\n"
		fi
	;;
	dont_stop_trans)
		rm -rf /usr/bin/trans_stop.sh > /dev/null 2>&1
		echo "**********************************************\n"
		echo "Disabled automatic stop transmission after downloads ..."
		echo "**********************************************\n"
	;;
	*)
	echo " "
	echo "Options: $0 {start|stop|enabled|disabled|create|on|off|stop_trans|dont_stop_trans}"
	echo " "
	exit 1
esac

exit 0