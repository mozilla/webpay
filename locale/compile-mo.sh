#!/bin/bash

# syntax:
# compile-mo.sh

echo "Compiling..."
for lang in `find . -type f -name "messages.po"`; do
    dir=`dirname $lang`
    stem=`basename $lang .po`
    msgfmt -o ${dir}/${stem}.mo $lang
done
