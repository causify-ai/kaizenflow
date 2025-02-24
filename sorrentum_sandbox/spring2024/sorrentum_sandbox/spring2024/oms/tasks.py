#
# //amp/oms/tasks.py
#
import logging

# We inline the code here since we need to make it visible to `invoke`,
# although `from ... import *` is a despicable approach.
from oms_lib_tasks import *  # noqa: F403 (unable to detect undefined names)

_LOG = logging.getLogger(__name__)
