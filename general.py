#/bin/env python2

## STUDENT
# The sudent database works like the sales database. The first stage
# of a student is an registration.
# A validated registration becomes a student.
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
            'Relationship to student',
            required=True),

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


class school_academic_period(osv.osv):
    _name = 'school.academic.period'
    _description = 'Academic Period'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'date_from': fields.date(
            'Start Date',
            select=True,
            help="Date of school opening"),
        'date_to': fields.date(
            'End Date',
            select=True,
            help="Date of school closing"),
        'class_ids': fields.one2many(
            'school.class',
            'year_id',
            'Classes for this Year'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('open', 'Current'),
            ('archived', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The archive status of this Year" ),
    }
    _defaults = {
        'state': "draft",
    }

    def archive_year(self, cr, uid, ids, context=None):
        class_obj = self.pool.get('school.class')
        for year in self.browse(cr, uid, ids, context=context):
            class_ids = class_obj.search(cr, uid, [('year_id','=',year.id)], context=context)
            class_obj.archive_class(cr, uid, class_ids, context=context)
        self.write(cr, uid, ids, {'state': 'archived'}, context=context)

    def set_current(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option can only be used for a single id at a time.'
        open_ids = self.search(cr, uid, [('state','=','open')], context=context)
        self.archive_year(cr, uid, open_ids, context=context)
        self.write(cr, uid, ids, {'state': 'open'}, context=context)

school_academic_period()


class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _description = 'Year'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'tuition_fee_id': fields.many2one(
            'product.product',
            'Default tuition Fee',
            domain=[('sale_ok','=',True)]),
        'description': fields.text('Description'),
    }
school_academic_year()


class school_teacher(osv.osv):
    _name = 'school.teacher'
    _description = 'Teacher'

    def _default_employee_id(self, cr, uid, context=None):
        return resolve_id_from_context('employee_id', context)

    _columns = {
        'name': fields.char('Teacher Name', size=255, select=True),
        'employee_id': fields.many2one(
            'hr.employee',
            'Employee'),
        'description': fields.text('Description'),
        'class_ids': fields.one2many(
            'school.class',
            'teacher_id',
            'Classes'),
        'state': fields.selection([
            ('open', 'Active'),
            ('archive', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The status of this Teacher" ),
    }

    _defaults = {
        'state': 'open',
        'employee_id': _default_employee_id,
    }

    def create(self, cr, uid, vals, context=None):
        hr_obj = self.pool.get('hr.employee')
        if vals.get('name', '/') == '/':
            vals['name'] = 'Unnamed Teacher'
            if vals.get('employee_id', False):
                employee = hr_obj.browse(cr, uid, vals['employee_id'], context)
                vals['name'] = employee.name
        return super(school_teacher, self).create(cr, uid, vals, context=context)

    def archive_teacher(self, cr, uid, ids, context=None):
        """Archives Teachers"""
        self.write(cr, uid, ids, {'state': 'archived'}, context=context)

school_teacher()


class school_class(osv.osv):
    _name = 'school.class'
    _description = 'Class'

    def _default_year_id(self, cr, uid, context=None):
        return resolve_id_from_context('year_id', context)

    def _default_level_id(self, cr, uid, context=None):
        return resolve_id_from_context('level_id', context)

    def _default_teacher_id(self, cr, uid, context=None):
        return resolve_id_from_context('teacher_id', context)

    _columns = {
        'name': fields.char('Name', size=255, select=True),
        'year_id': fields.many2one(
            'school.academic.period',
            'Academic period',
            domain=[('state','=','open')],
            required=True),
        'level_id': fields.many2one(
            'school.academic.year',
            'Year',
            required=True),
        'teacher_id': fields.many2one(
            'school.teacher',
            'Class (Homeroom) Teacher',
            required=True),
        'enrolment_ids': fields.one2many(
            'school.enrolment',
            'class_id',
            'Class Roll',
            domain=[('state','=','enrolled')]),
        'state': fields.selection([
            ('open', 'Enrolments open'),
            ('closed', 'Enrolments closed'),
            ('archive', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The status of this Class" ),
    }
    _defaults = {
        'name': '/',
        'state': 'open',
        'year_id': _default_year_id,
        'level_id': _default_level_id,
        'teacher_id': _default_teacher_id,
    }

    _sql_constraints = [(
        'year_level_teacher_unique',
        'unique (year_id, level_id, teacher_id)',
        'This class already exists!'),
    ]

    def create(self, cr, uid, vals, context=None):
        teacher_obj = self.pool.get('school.teacher')
        level_obj = self.pool.get('school.academic.year')
        year_obj = self.pool.get('school.academic.period')
        if vals.get('name', '/') == '/':
            teacher = teacher_obj.browse(cr, uid, vals['teacher_id'], context)
            level = level_obj.browse(cr, uid, vals['level_id'], context)
            year = year_obj.browse(cr, uid, vals['year_id'], context)
            vals['name'] = ' '.join([level.name, teacher.name, year.name])
        return super(school_class, self).create(cr, uid, vals, context=context)

    def close_class(self, cr, uid, ids, context=None):
        """lock class for enrolments"""
        self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def open_class(self, cr, uid, ids, context=None):
        """re-open class for enrolments"""
        self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def archive_class(self, cr, uid, ids, context=None):
        """Archives class and releases students for new enrolment"""
        student_ids = []
        enr_ids = []
        for sclass in self.browse(cr, uid, ids, context=context):
            for enr in sclass.enrolment_ids:
                enr_ids.append(enr.id)
        enr_obj = self.pool.get('school.enrolment')
        enr_obj.enrolment_archive(cr, uid, enr_ids, context=context)
        self.write(cr, uid, ids, {'state': 'archived'}, context=context)

school_class()
