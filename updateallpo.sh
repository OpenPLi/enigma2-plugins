#!/bin/bash
# Script to generate po files outside of the normal build process
#  
# Pre-requisite:
# The following tools must be installed on your system and accessible from path
# gawk, find, xgettext, sed, python, msguniq, msgmerge, msgattrib, msgfmt, msginit
#
# Run this script from the top folder of enigma2-plugins
#
#
# Author: Pr2 for OpenPLi Team
# Version: 1.1

rootpath=$PWD
localgsed="sed"
findoptions=""

#
# Script only run with gsed but on some distro normal sed is already gsed so checking it.
#
gsed --version 2> /dev/null | grep -q "GNU"
if [ $? -eq 0 ]; then
	localgsed="gsed"
else
	"$localgsed" --version | grep -q "GNU"
	if [ $? -eq 0 ]; then
		printf "GNU sed found: [%s]\n" $localgsed
	fi
fi

#
# python version check that we are with python3
#
python_exec=""
which python3 > /dev/null 2>&1
if [[ $? -eq 0 ]]; then
	python_exec="python3"
else
	which python > /dev/null 2>&1
	if [[ $? -eq 0 ]]; then
		# Check if it is version 3
		python_version=$(python --version | awk -F "." '{ gsub(/Python\s+/,"",$1); print $1; }')
		if [[ ${python_version} -eq 3 ]]; then
			python_exec="python"
		else
			python_exec=""
		fi
	fi
fi
[[ -z ${python_exec} ]] && { echo "No python 3 found, please install it or set it first into your PATH variable"; exit 1; }

echo "Python  found: [${python_exec}]"

#
# On Mac OSX find option are specific
#
if [[ "$OSTYPE" == "darwin"* ]]
	then
		# Mac OSX
		printf "Script running on Mac OSX [%s]\n" "$OSTYPE"
    	findoptions=" -s -X "
fi
#
# Parsing the folders tree
#
printf "Po files update/creation from script starting.\n"
for directory in */po/ ; do
	cd $rootpath/$directory
	#
	# Update Makefile.am to include all existing language files sorted
	#
	makelanguages=$(ls *.po | tr "\n" " " | $localgsed 's/.po//g')
	$localgsed -i 's/LANGS.*/LANGS = '"$makelanguages"'/' Makefile.am
	# git add Makefile.am
    #
	# Retrieve languages and plugin name from Makefile.am LANGS @ PLUGIN variables for backward compatibility
	#
	languages=($(gawk ' BEGIN { FS=" " } 
			/^LANGS/ {
				for (i=3; i<=NF; i++)
					printf "%s ", $i
			} ' Makefile.am ))
	#
	# To update only existing files regardless of the defined ones in Makefile.am
	#
	# languages=($(ls *.po | tr "\n" " " | $localgsed 's/.po//g'))
	plugin=$(gawk ' BEGIN { FS=" " } /^PLUGIN/ { print $3 }' Makefile.am)
	printf "Processing plugin %s\n" $plugin
	#
	printf "Creating temporary file $plugin-py.pot\n"
	find $findoptions .. -name "*.py" -exec xgettext --no-wrap -L Python --from-code=UTF-8 -kpgettext:1c,2 --add-comments="TRANSLATORS:" -d $plugin -s -o $plugin-py.pot {} \+
	$localgsed --in-place $plugin-py.pot --expression=s/CHARSET/UTF-8/
	printf "Creating temporary file $plugin-xml.pot\n"
	find $findoptions .. -name "*.xml" -exec ${python_exec} $rootpath/xml2po-python3.py {} \+ > $plugin-xml.pot
	printf "Merging pot files to create: %s.pot\n" $plugin
	cat $plugin-py.pot $plugin-xml.pot | msguniq --no-wrap --no-location -o $plugin.pot -
	rm $plugin-py.pot $plugin-xml.pot
	# git add $plugin.pot
	OLDIFS=$IFS
	IFS=" "
	for lang in "${languages[@]}" ; do
		if [ -f $lang.po ]; then \
			printf "Updating existing translation file $lang.po\n"; \
			msgmerge --backup=none --no-wrap --no-location -s -U $lang.po $plugin.pot && touch $lang.po; \
			msgattrib --no-wrap --no-obsolete $lang.po -o $lang.po; \
			msgfmt -o $lang.mo $lang.po; \
			# git add -f $lang.po; \
		else \
			printf "New file created: $lang.po, please add it to # github before commit\n"; \
			msginit -l $lang.po -o $lang.po -i $plugin.pot --no-translator; \
			msgfmt -o $lang.mo $lang.po; \
			# git add -f $lang.po; \
		fi
	done
	IFS=$OLDIFS 
	# git commit -m "Plugin $plugin po files updated at $(date +"%Y-%m-%d %H:%M")"
done
# git push
cd $rootpath/
printf "Po files update/creation from script finished!\n"


