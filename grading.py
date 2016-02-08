#/bin/env python2

## enrolment

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
_logger = logging.getLogger(__name__)

class school_subject(osv.osv):
    _name = 'school.subject'

    _columns = {
        'name': fields.char('Subject', size=255, required=True),
        'grading_method': fields.selection([
            ('numeric', 'Numeric'),
            ('alpha', 'Alphabetic')],
            'Grading method',
            select=True),
        'description': fields.text('Description'),
    }

    def get_grading_method(self, cr, uid, sub_id, context=None):
        sub = self.browse(cr, uid, sub_id, context=context)
        if sub:
            return sub.grading_method
        return False
school_subject()


class school_teacher(osv.osv):
    _name = 'school.teacher'
    _inherit = 'school.teacher'

    _columns = {
        'subject_ids': fields.many2many(
            'school.subject',
            'teacher_subject_rel',
            'teacher_id',
            'subject_id',
            'Subjects'),
    }
school_teacher()


class school_grade(osv.osv):
    _name = 'school.grade'

    def _default_enrolment_id(self, cr, uid, context=None):
        return resolve_id_from_context('enrolment_id', context)

    def _default_teacher_id(self, cr, uid, context=None):
        return resolve_id_from_context('teacher_id', context)

    def _default_subject_id(self, cr, uid, context=None):
        return resolve_id_from_context('subject_id', context)

    def onchange_subject_id(self, cr, uid, ids, sub_id, context=None):
        """Try and get grading method from subject."""
        sub_obj = self.pool.get('school.subject')
        grd = False
        if sub_id:
            grd = sub_obj.get_grading_method(cr, uid, sub_id, context=context)
        return {'value': {'grading_method': grd}}

    def _display_grade(self, cr, uid, ids, name, args, context=None):
        if not ids:
            return {}
        res = {}
        for l in self.browse(cr, uid, ids, context=context):
            if l.grading_method == 'numeric':
                res[l.id] = ' / '.join([str(l.numeric_val), str(l.numeric_ceil)])
            if l.grading_method == 'alpha':
                res[l.id] = l.alpha_val
        return res

    _columns = {
        'name': fields.char('Grade for', size=255, required=True,),
        'enrolment_id': fields.many2one(
            'school.enrolment',
            'Student',
            required=True,
            ondelete='cascade'),
        'teacher_id': fields.many2one(
            'school.teacher',
            'Teacher',
            required=True),
        'subject_id': fields.many2one(
            'school.subject',
            'Subject',
            required=True),
        'date': fields.date('Grade Date', required=True),
        'grading_method': fields.selection([
            ('numeric', 'Numeric'),
            ('alpha', 'Alphabetic')],
            'Grading method',
            select=True,
            required=True),
        'numeric_ceil': fields.integer("Maximum"),
        'numeric_val': fields.float("Value"),
        'alpha_val': fields.selection([
            ('100', 'A+'),
            ('90', 'A'),
            ('80', 'B+'),
            ('70', 'B'),
            ('60', 'C+'),
            ('50', 'C'),
            ('40', 'D+'),
            ('30', 'D'),
            ('20', 'E+'),
            ('10', 'E'),
            ('5', 'F+'),
            ('0', 'F')],
            'Value',
            select=True),
        'value': fields.function(
            _display_grade,
            string='Grade',
            type='char'),
        'description': fields.text('Comment'),
    }

    _defaults = {
        'name': "/",
        'date': fields.date.context_today,
        'enrolment_id': _default_enrolment_id,
        'teacher_id': _default_teacher_id,
        'subject_id': _default_subject_id,
    }

    def create(self, cr, uid, vals, context=None):
        sub_obj = self.pool.get('school.subject')
        reg_obj = self.pool.get('school.enrolment')
        sub = sub_obj.browse(cr, uid, vals['subject_id'], context=context)
        reg = reg_obj.browse(cr, uid, vals['enrolment_id'], context=context)
        class_obj = self.pool.get('school.class')
        if vals.get('name', '/') == '/':
            vals['name'] = '-'.join([sub.name, reg.name])
        return super(school_grade, self).create(cr, uid, vals, context=context)
school_grade()


class school_enrolment(osv.osv):
    _name = 'school.enrolment'
    _inherit = 'school.enrolment'
    _columns = {
        'grade_ids': fields.one2many(
            'school.grade',
            'enrolment_id',
            'Grades'),
    }
school_enrolment()


class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _inherit = 'school.academic.year'
    _columns = {
        'subject_ids': fields.many2many(
            'school.subject',
            'level_subject_rel',
            'level_id',
            'subject_id',
            'Subjects'),
    }
school_academic_year()
