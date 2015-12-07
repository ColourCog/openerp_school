#/bin/env python2

import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_religion(osv.osv):
    _name = 'school.religion'

    _columns = {
        'name': fields.char('Religion', size=255, select=True, readonly=True),
    }

school_religion()


class school_language(osv.osv):
    _name = 'school.language'

    _columns = {
        'name': fields.char('Language', size=255, select=True, readonly=True),
    }

school_language()

class school_student_relative(osv.osv):
    _name = 'school.student.relative'

    _columns = {
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'partner_id': fields.many2one('res.partner', 'Relative', required=True),
        'relationship': fields.selection([
            ('father', 'Father'),
            ('mother', 'Mother'),
            ('guardian', 'Guardian'),
            ]),

    }
    _sql_constraints = [(
        'student_relative_unique',
        'unique (student_id, partner_id)',
        'Relatives must be unique per Student !'),
    ]

school_student_relative()



class school_student(osv.osv):
    _name = 'school.student'
    _description = 'Student'
    _columns = {
        'surname': fields.char('Family Name', size=255, select=True, readonly=True),
        'firstname': fields.char('First Name(s)', size=255, select=True, readonly=True),
        'gender': fields.selection([
            ('m', 'Male'),
            ('f', 'Female')], required=True),
        'birthday': fields.date('Date of birth', required=True),
        'birthplace': fields.char('Place of birth', size=255),
        'nationality_id': fields.many2one('res.country', 'Nationality', required=True),
        'nationality_ids': fields.many2many(
            'res.country',
            'student_country_rel',
            'student_id',
            'country_id',
            'Other Nationalities'),
        'religion_id': fields.many2one('school.religion', 'Family Religion', required=True),
        'language_id': fields.many2one('school.language', 'First Language', required=True),
        'language_ids': fields.many2many(
            'school.language',
            'student_language_rel',
            'student_id',
            'language_id',
            'Other Languages'),
        'relative_ids': fields.one2many(
            'school.student.relative',
            'student_id',
            'Relative or Guardian'),
        'billing_partner_id': fields.many2one('res.partner', 'Billing', required=True),
    }
school_student()
