#/bin/env python2

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
        'name': fields.char('Name', size=64),
        'date_end': fields.date(
            'End date',
            required=True,
            select=True),
        'date_start': fields.date(
            'Start date',
            required=True,
            select=True),
    }
school_academic_year()


class school_academic_grade(osv.osv):
    _name = 'school.academic.grade'
    _description = 'Academic Grade'
    _columns = {
        'name': fields.char('Name', size=128),
    }
school_academic_grade()
