#/bin/env python2

## CLASS

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
_logger = logging.getLogger(__name__)

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
            ('archived', 'Archived')],
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

    def copy(self, cr, uid, class_id, default=None, context=None):
        if not context:
            context = {}
        if not default:
            default = {}
        default.update({
            'state':'open',
            'year_id': contex.get('default_year_id'),
            })
        new_id = super(school_class, self).copy(cr, uid, class_id, default, context=context)
        return new_id

    def close_class(self, cr, uid, ids, context=None):
        """lock class for enrolments"""
        self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def open_class(self, cr, uid, ids, context=None):
        """(re)open class for enrolments"""
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
