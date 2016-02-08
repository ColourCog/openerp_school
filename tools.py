#/bin/env python2

import time
import logging

_logger = logging.getLogger(__name__)

def resolve_id_from_context(target, context=None):
    if context is None:
        context = {}
    if type(context.get(target)) in (int, long):
        return context[target]
    return None
