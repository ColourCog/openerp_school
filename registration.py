#/bin/env python2

## REGISTRATION

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _description = 'Academic Year'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
    }

school_academic_year()

class school_academic_level(osv.osv):
    _name = 'school.academic.level'
    _description = 'Academic Level'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
    }

school_academic_level()

class school_class(osv.osv):
    _name = 'school.class'
    _description = 'Class'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
    }

school_class()
