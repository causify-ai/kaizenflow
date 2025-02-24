#!/bin/bash
source /Users/saggese/src/venv/amp.client_venv/bin/activate
echo "$@"
/Users/saggese/src/venv/amp.client_venv/bin/nb-clean clean $@
exit 0
