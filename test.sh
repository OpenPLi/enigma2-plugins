#!/bin/bash

for DIR in *; do
	if [ -d $DIR/src ]; then
		if [ -f $DIR/src/Makefile.am ]; then
			NAME=`grep installdir $DIR/src/Makefile.am`
			if [ -z "$NAME" ]; then
				NAME=`grep plugindir $DIR/src/Makefile.am`
			fi
			NAME=${NAME%/}
			echo mv $DIR ${NAME##*/}
		fi
	fi
done
