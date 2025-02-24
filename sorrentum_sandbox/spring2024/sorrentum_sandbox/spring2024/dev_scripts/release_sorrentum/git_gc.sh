#!/bin/bash -x
du -d 1 -h .
git -c gc.reflogExpire=0 \
    -c gc.reflogExpireUnreachable=0 \
    -c gc.rerereresolved=0 \
    -c gc.rerereunresolved=0 \
    -c gc.pruneExpire=now \
    gc
#git gc
du -d 1 -h .
