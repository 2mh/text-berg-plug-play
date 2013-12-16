#!/bin/bash
# Ask h2m@access.uzh.ch
cat $1 | grep '</s>' -B 1 | cut -d '>' -f2 | grep "<" | sed -e 's|</w||' | sort -u
