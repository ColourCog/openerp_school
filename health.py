#/bin/env python2

## STUDENT
# The sudent database works like the sales database. The first stage
# of a student is an enrolment.
# A validated enrolment becomes a student.
# The views are the ones that make the difference; especially
# the fields_view_get

import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_health_line(osv.osv):
    _name = 'school.health.line'

    _columns = {
        'health_id': fields.many2one('school.health', 'Health', required=True),
        'date': fields.date('Date'),
        'name': fields.text('Checkup Detail', required=True),
        'recommendation': fields.text('Checkup Recommendation'),

    }
    _defaults = {
        'date': fields.date.context_today,
    }

school_health_line()


class school_health(osv.osv):
    _name = 'school.health'
    _description = "Health Detail for Student"

    _columns = {
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'name': fields.related(
            'student_id',
            'name',
            type='char',
            relation='school.student',
            string="Student Name"),
        'height': fields.float('Height(cm)'),
        'weight': fields.float('Weight (kgs)'),
        'blood_group': fields.selection([
            ('A+', 'A+ve'),
            ('B+', 'B+ve'),
            ('O+', 'O+ve'),
            ('AB+', 'AB+ve'),
            ('A-', 'A-ve'),
            ('B-', 'B-ve'),
            ('O-', 'O-ve'),
            ('AB-', 'AB-ve')],
            'Blood Group'),
        'eye_glasses': fields.boolean('Eye Glasses?'),
        'eye_glasses_no': fields.char('Eye Glasses', size=64),
        'physical_challenges': fields.boolean('Physical Challenge?'),
        'physical_challenges_note': fields.text('Physical Challenge'),
        'allergies': fields.boolean('Allergies?'),
        'allergies_note': fields.text('Allergies'),
        'special_diet': fields.boolean('Special Diet?'),
        'special_diet_note': fields.text('Special Diet'),
        'regular_checkup': fields.boolean('Any Regular Checkup Required?'),
        'previous_ids': fields.one2many(
            'school.health.line',
            'health_id',
            'Checkup Lines'),

    }
school_health()


class school_student(osv.osv):
    _inherit = 'school.student'
    _columns = {
        'health_ids': fields.one2many(
            'school.health',
            'student_id',
            'Medical Status'),
    }
school_student()
