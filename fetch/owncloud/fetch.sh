#!/bin/bash

if [ "$1" = "-h" ]; then
	echo "KEY_FETCH=<the key> ./fetch.sh"
	exit 1
fi

set -e

[[ -e .tmp ]] && rm -rf .tmp
mkdir .tmp

echo "Clean up data"
rm -rf files meta_features instances

KEY_FETCH=${KEY_FETCH-tSrHBNFemfKIVuY}

echo "Download the zip file"
out=`date +test-%a.zip`
wget -q -O $out https://cloud.msf.org/index.php/s/${KEY_FETCH}/download
DIRNAME=$(unzip -qql $out | head -n1 | tr -s ' ' | cut -d' ' -f5-)

cp $out .tmp/tests.zip
cd .tmp

echo "Unzip"
unzip tests.zip

cp -R $DIRNAME/* ../

cd ..
rm -rf .tmp

