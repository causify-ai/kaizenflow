#!/bin/bash -e
TMUX_SESSION=$(tmux display-message -p '#S')
echo "TMUX_SESSION=$TMUX_SESSION"

tmux kill-session -t $TMUX_SESSION
