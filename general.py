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
    _sql_constraints = [(
        'checklist_unique',
        'unique (name)',
        'Checklist name must be unique'),
    ]
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


class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _description = 'Academic Year'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'class_ids': fields.one2many(
            'school.class',
            'year_id',
            'Classes for this Year'),
        'state': fields.selection([
            ('open', 'Current'),
            ('archived', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The archive status of this Year" ),
    }
    _defaults = {
        'state': "open",
    }

    def close_year(self, cr, uid, ids, context=None):
        class_ids = []
        class_obj = self.pool.get('school.class')
        for year in self.browse(cr, uid, ids, context=context):
            class_ids.extend(
                class_obj.search(
                    cr,
                    uid,
                    [('year_id','=',year.id)],
                    context=context))
        class_obj.archive_class(cr, uid, class_ids, context=context)
        self.write(cr, uid, ids, {'state': 'archived'}, context=context)
school_academic_year()


class school_academic_level(osv.osv):
    _name = 'school.academic.level'
    _description = 'Academic Level'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'tuition_fee_id': fields.many2one(
            'product.product',
            'Default tuition Fee'),
        'description': fields.text('Description'),
    }
school_academic_level()


class school_teacher(osv.osv):
    _name = 'school.teacher'
    _description = 'Teacher'

    _columns = {
        'name': fields.char('Teacher Name', size=255, select=True),
        'employee_id': fields.many2one(
            'hr.employee',
            'Employee'),
    }
    def create(self, cr, uid, vals, context=None):
        hr_obj = self.pool.get('hr.employee')
        if vals.get('name', '/') == '/':
            vals['name'] = 'Unnamed Teacher'
            if vals.get('employee_id', False):
                employee = hr_obj.browse(cr, uid, vals['employee_id'], context)
                vals['name'] = employee.name
        return super(school_teacher, self).create(cr, uid, vals, context=context)
school_teacher()


class school_class(osv.osv):
    _name = 'school.class'
    _description = 'Class'

    _columns = {
        'name': fields.char('Name', size=255, select=True),
        'year_id': fields.many2one(
            'school.academic.year',
            'Academic Year',
            domain=[('state','=','open')],
            required=True),
        'level_id': fields.many2one(
            'school.academic.level',
            'Year',
            required=True),
        'teacher_id': fields.many2one(
            'school.teacher',
            'Class (Homeroom) Teacher',
            required=True),
        'registration_ids': fields.one2many(
            'school.registration',
            'class_id',
            'Class Roll'),
        'state': fields.selection([
            ('open', 'Registrations open'),
            ('closed', 'Registrations closed'),
            ('archive', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The status of this Class" ),
    }
    _defaults = {
        'state': 'open',
    }
    _sql_constraints = [(
        'level_year_unique',
        'unique (year_id, level_id)',
        'Level must be unique per Year !'),
    ]

    def create(self, cr, uid, vals, context=None):
        teacher_obj = self.pool.get('school.teacher')
        level_obj = self.pool.get('school.academic.level')
        year_obj = self.pool.get('school.academic.year')
        if vals.get('name', '/') == '/':
            teacher = teacher_obj.browse(cr, uid, vals['teacher_id'], context)
            level = level_obj.browse(cr, uid, vals['level_id'], context)
            year = year_obj.browse(cr, uid, vals['year_id'], context)
            vals['name'] = ' '.join([level.name, teacher.name, year.name])
        return super(school_class, self).create(cr, uid, vals, context=context)

    def close_class(self, cr, uid, ids, context=None):
        """Archives class and releases students for new registration"""
        student_ids = []
        for sclass in self.browse(cr, uid, ids, context=context):
            for reg in sclass.registration_ids:
                student_ids.append(reg.student_id.id)
        student_obj = self.pool.get('school.student')
        student_obj.write(cr, uid, student_ids, {'current_class_id': None}, context=context)
        self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def archive_class(self, cr, uid, ids, context=None):
        """Archives class and releases students for new registration"""
        student_ids = []
        for sclass in self.browse(cr, uid, ids, context=context):
            for reg in sclass.registration_ids:
                student_ids.append(reg.student_id.id)
        student_obj = self.pool.get('school.student')
        student_obj.write(cr, uid, student_ids, {'current_class_id': None}, context=context)
        self.write(cr, uid, ids, {'state': 'archived'}, context=context)

school_class()
