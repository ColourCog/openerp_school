#/bin/env python2

## STUDENT
# The sudent database works like the sales database. The first stage
# of a student is an enrolment.
# A validated enrolment becomes a student.
# The views are the ones that make the difference; especially
# the fields_view_get

import time
import logging

_logger = logging.getLogger(__name__)

def resolve_id_from_context(target, context=None):
    if context is None:
        context = {}
    if type(context.get(target)) in (int, long):
        return context[target]
    return None
