#!/bin/bash
# Takes a screenshot to the clipboard then saves the
# clipboard image to a file in jpeg format.
#
# Usage: screenshot_save.sh[[path/]filename]
#
# If no filename is specified, the image will be saved to the present working
# directory and named using the current date and time.  If more than one
# argument is given, all but the first argument are ignored.
#
# e.g.
# > screenshot_save.sh
# > screenshot_save.sh ~/Desktop
# > screenshot_save.sh ~/Desktop/foo.jpg
# > screenshot_save.sh /Users/saggese/src/git_gp1/notes/figs/game_theory/week4.pure_strategies_example.png

# In practice it is
# > screencapture -c -i -t png notes/figs/game_theory/week4.pure_strategies_example.png

screencapture -c -i

folder=$(pwd)
filename=$(date +%Y-%m-%d\ at\ %H.%M.%S).jpg

if [ $# -ne 0 ]; then
    if [[ -d $1 ]]; then
        if [ "$1" != "." ]; then folder=$1; fi
    else
        a=$(dirname "$1")
        b=$(basename "$1" .jpg)

        if [ "$b" != "" ]; then filename=$b.jpg; fi

        if [ "$a" != "." ]; then folder=$a; fi
    fi
fi

osascript -e "tell application \"System Events\" to ¬
        write (the clipboard as JPEG picture) to ¬
        (make new file at folder \"$folder\" ¬
        with properties {name:\"$filename\"})"
