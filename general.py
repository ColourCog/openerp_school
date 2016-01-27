#/bin/env python2

## STUDENT
# The sudent database works like the sales database. The first stage
# of a student is an enrolment.
# A validated enrolment becomes a student.
# The views are the ones that make the difference; especially
# the fields_view_get

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
_logger = logging.getLogger(__name__)

class school_school(osv.osv):
    _name = 'school.school'
    _description = 'School'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'website': fields.char('Website', size=64, help="School website"),
    }

school_school()


class school_religion(osv.osv):
    _name = 'school.religion'

    _columns = {
        'name': fields.char('Religion', size=255),
    }

school_religion()


class school_language(osv.osv):
    _name = 'school.language'

    _columns = {
        'name': fields.char('Language', size=255),
    }

school_language()


class school_student_education(osv.osv):
    _name = 'school.student.education'

    _columns = {
        'name': fields.related(
            'school_id',
            'name',
            type='char',
            relation='school.school',
            string="School Name"),
        'student_id': fields.many2one(
            'school.student',
            'Student',
            required=True,
            ondelete='cascade'),
        'school_id': fields.many2one('school.school', 'Previous School', required=True),
        'date_from': fields.date('From'),
        'date_to': fields.date('To'),

    }

school_student_education()


class school_student_relative(osv.osv):
    _name = 'school.student.relative'

    _columns = {
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'partner_id': fields.many2one(
            'res.partner',
            'Relative',
            required=True,
            domain=[('customer','=',True)]),
        'relationship': fields.selection([
            ('father', 'Father'),
            ('mother', 'Mother'),
            ('guardian', 'Guardian')],
            'Relationship to student'),

    }
    _sql_constraints = [(
        'student_relative_unique',
        'unique (student_id, partner_id)',
        'Relationship must be unique per Student !'),
    ]

school_student_relative()

class school_checklist(osv.osv):
    _name = "school.checklist"
    _description = "Category of Required Item"
    _columns = {
        "name": fields.char("Name", size=100, required=True),
    }
school_checklist()


class school_checklist_item(osv.osv):
    _name = "school.checklist.item"
    _description = "Required item"

    _columns = {
        "checklist_id": fields.many2one("school.checklist", "Category",
                                   required=True),
        "name": fields.char("Name", size=100, required=True),
    }
school_checklist_item()
