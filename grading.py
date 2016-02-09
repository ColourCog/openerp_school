#/bin/env python2

## enrolment

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
from tools import GRADING_METHOD, ALPHA_GRADING, ALPHA_DICT
_logger = logging.getLogger(__name__)

class school_subject(osv.osv):
    _name = 'school.subject'

    def _default_grading_method(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_grading_method:
            return user.company_id.default_grading_method
        return 'alpha'

    _columns = {
        'name': fields.char('Subject', size=255, required=True),
        'grading_method': fields.selection(
            GRADING_METHOD,
            'Grading method',
            select=True),
        'description': fields.text('Description'),
    }

    _defaults = {
        'grading_method': _default_grading_method,
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


class school_year_subject(osv.osv):
    _name = 'school.year.subject'
    _description = 'Subjects per Year'

    def _default_level_id(self, cr, uid, context=None):
        return resolve_id_from_context('level_id', context)

    def _default_subject_id(self, cr, uid, context=None):
        return resolve_id_from_context('subject_id', context)

    def _default_grading_method(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_grading_method:
            return user.company_id.default_grading_method
        return 'alpha'

    _columns = {
        'level_id': fields.many2one(
            'school.academic.year',
            'Year',
            required=True),
        'subject_id': fields.many2one(
            'school.subject',
            'Subject',
            required=True),
        'grading_method': fields.selection([
            ('numeric', 'Numeric'),
            ('alpha', 'Alphabetic')],
            'Grading method',
            select=True),
        'weight': fields.float('Weight'),
    }

    _defaults = {
        'level_id': _default_level_id,
        'subject_id': _default_subject_id,
        'grading_method': _default_grading_method,
        'weight': 1.0,
    }

    _sql_constraints = [(
        'subject_level_unique',
        'unique (level_id, subject_id)',
        'Subject must be unique per Year !'),
    ]

    def get_grading_method(self, cr, uid, sub_id, context=None):
        sub = self.browse(cr, uid, sub_id, context=context)
        if sub:
            return sub.grading_method
        return False

    def get_weight(self, cr, uid, level_id, subject_id, context=None):
        sub_id = self.search(cr, uid, [('level_id','=',level_id),('subject_id','=',subject_id)], context=context)
        sub = self.browse(cr, uid, sub_id, context=context)
        if sub:
            return sub.weight
        return 1.0

school_year_subject()


class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _inherit = 'school.academic.year'

    _columns = {
        'subject_ids': fields.one2many(
            'school.year.subject',
            'level_id',
            'Subjects'),
    }

school_academic_year()


class school_class_subject(osv.osv):
    _name = 'school.class.subject'
    _description = 'Subjects per Class'

    def _default_class_id(self, cr, uid, context=None):
        return resolve_id_from_context('class_id', context)

    def _default_subject_id(self, cr, uid, context=None):
        return resolve_id_from_context('subject_id', context)

    def _default_teacher_id(self, cr, uid, context=None):
        return resolve_id_from_context('teacher_id', context)

    def _default_grading_method(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_grading_method:
            return user.company_id.default_grading_method
        return 'alpha'

    _columns = {
        'class_id': fields.many2one(
            'school.class',
            'class',
            required=True),
        'subject_id': fields.many2one(
            'school.subject',
            'Subject',
            required=True),
        'teacher_id': fields.many2one(
            'school.teacher',
            'Teacher',
            required=True),
        'grading_method': fields.selection([
            ('numeric', 'Numeric'),
            ('alpha', 'Alphabetic')],
            'Grading method',
            select=True),
        'weight': fields.float('Weight'),
    }

    _defaults = {
        'class_id': _default_class_id,
        'subject_id': _default_subject_id,
        'teacher_id': _default_teacher_id,
        'grading_method': _default_grading_method,
        'weight': 1.0,
    }

    _sql_constraints = [(
        'subject_class_unique',
        'unique (class_id, subject_id)',
        'Subject must be unique per class !'),
    ]

    def get_grading_method(self, cr, uid, sub_id, context=None):
        sub = self.browse(cr, uid, sub_id, context=context)
        if sub:
            return sub.grading_method
        return False

    def get_weight(self, cr, uid, class_id, subject_id, context=None):
        sub_id = self.search(cr, uid, [('class_id','=',class_id),('subject_id','=',subject_id)], context=context)
        sub = self.browse(cr, uid, sub_id, context=context)
        if sub:
            return sub.weight
        return 1.0

school_class_subject()


class school_class(osv.osv):
    _name = 'school.class'
    _inherit = 'school.class'

    _columns = {
        'subject_ids': fields.one2many(
            'school.class.subject',
            'class_id',
            'Subjects'),
    }

school_class()

class school_grade(osv.osv):
    _name = 'school.grade'

    def _default_enrolment_id(self, cr, uid, context=None):
        return resolve_id_from_context('enrolment_id', context)

    def _default_teacher_id(self, cr, uid, context=None):
        return resolve_id_from_context('teacher_id', context)

    def _default_subject_id(self, cr, uid, context=None):
        return resolve_id_from_context('subject_id', context)

    def onchange_subject_id(self, cr, uid, ids, sub_id, context=None):
        """Try and get grading method."""
        sub_obj = self.pool.get('school.subject')
        grd = False
        if sub_id:
            #TODO: try the Year first
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
                res[l.id] = ALPHA_DICT.get(l.alpha_val, False)
        return res

    def _get_weight(self, cr, uid, subject_id, enr_id, context=None):
        enr_obj = self.pool.get('school.enrolment')
        enr = enr_obj.browse(cr, uid, enr_id, context=context)
        level_id = enr.class_id.level_id.id
        sub_obj = self.pool.get('school.year.subject')

        return sub_obj.get_weight(cr, uid, level_id, subject_id, context=context)

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
        'alpha_val': fields.selection(
            ALPHA_GRADING,
            'Value',
            select=True),
        'value': fields.function(
            _display_grade,
            string='Grade',
            type='char'),
        'weight': fields.float('Weight'),
        'description': fields.text('Comment'),
    }

    _defaults = {
        'name': "/",
        'date': fields.date.context_today,
        'enrolment_id': _default_enrolment_id,
        'teacher_id': _default_teacher_id,
        'subject_id': _default_subject_id,
        'weight': 1,
    }

    def create(self, cr, uid, vals, context=None):
        sub_obj = self.pool.get('school.subject')
        reg_obj = self.pool.get('school.enrolment')
        sub = sub_obj.browse(cr, uid, vals['subject_id'], context=context)
        reg = reg_obj.browse(cr, uid, vals['enrolment_id'], context=context)
        class_obj = self.pool.get('school.class')
        if vals.get('name', '/') == '/':
            vals['name'] = '-'.join([sub.name, reg.name])
        #TODO: get weight from year
        vals['weight'] = self._get_weight(
            cr,
            uid,
            vals['subject_id'],
            vals['enrolment_id'],
            context=context)
        return super(school_grade, self).create(cr, uid, vals, context=context)
school_grade()
