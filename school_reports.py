#/bin/env python2

## enrolment

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
from tools import generic_generate_invoice
_logger = logging.getLogger(__name__)


class school_enrolment(osv.osv):
    _inherit = 'school.enrolment'

    def print_report(self, cr, uid, ids, context=None):
        pass

school_enrolment()


class school_student(osv.osv):
    _inherit = 'school.student'

    def print_report(self, cr, uid, ids, context=None):
        report_map = {
            'family': 'school.student.print.family',
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_map.get(context.get('format')),
            'datas': {
                    'model':'school.student',
                    'id': ids and ids[0] or False,
                    'ids': ids and ids or [],
                    'report_type': 'pdf'
                },
            'nodestroy': True
        }

school_student()

class school_class(osv.osv):
    _inherit = 'school.class'

    def print_report(self, cr, uid, ids, context=None):
        report_map = {
            'surname': 'school.class.print.surname',
            'provisional': 'school.class.print.provisional',
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_map.get(context.get('format')),
            'datas': {
                    'model': 'school.class',
                    'id': ids and ids[0] or False,
                    'ids': ids and ids or [],
                    'report_type': 'pdf'
                },
            'nodestroy': True
        }

school_class()
