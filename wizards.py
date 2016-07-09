#/bin/env python2

## Custom wizards
#~ The wizards here are utilities to ease certain actions that, while
#~ not common, are still useful to have.

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
from tools import generic_generate_invoice
_logger = logging.getLogger(__name__)


class school_student_invoice(osv.osv_memory):
    """
    This wizard import an invoice into a registration
    """

    _name = "school.student.invoice"
    _description = "Import Invoice into registration"

    def _default_partner_id(self, cr, uid, context=None):
        return resolve_id_from_context('partner_id', context)

    _columns = {
        'partner_id': fields.many2one(
            'res.partner',
            'Partner',
            required=True),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Invoice to import',
            required=True),
    }

    _defaults = {
        'partner_id': _default_partner_id,
    }

    def import_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        reg_obj = pool_obj.get('school.student')
        reg = reg_obj.browse(cr, uid, context.get('active_id'), context=context)

        res = {
            'invoice_id': self.browse(cr, uid, ids)[0].invoice_id.id,
            'is_invoiced': True,
            }

        reg_obj.write(cr, uid, [context.get('active_id')], res, context=context)

        return {'type': 'ir.actions.act_window_close'}

school_student_invoice()


class school_enrolment_invoice(osv.osv_memory):
    """
    This wizard import an invoice into a enrolment
    """

    _name = "school.enrolment.invoice"
    _description = "Import Invoice into enrolment"

    def _default_student_id(self, cr, uid, context=None):
        return resolve_id_from_context('student_id', context)

    def onchange_student_id(self, cr, uid, ids, student_id, ctx=None):
        student = self.pool.get('school.student').browse(
            cr,
            uid,
            student_id, context=ctx)
        if student:
            return {'value': {'partner_id': student.billing_partner_id.id}}

    _columns = {
        'student_id': fields.many2one(
            'school.student',
            'Student',
            required=True),
        'partner_id': fields.many2one(
            'res.partner',
            'Partner',
            required=True),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Invoice to import',
            required=True),
    }

    _defaults = {
        'student_id': _default_student_id,
    }

    def import_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        enr_obj = pool_obj.get('school.enrolment')
        enr = enr_obj.browse(cr, uid, context.get('active_id'), context=context)

        res = {
            'invoice_id': self.browse(cr, uid, ids)[0].invoice_id.id,
            'is_invoiced': True,
            }

        enr_obj.write(cr, uid, [context.get('active_id')], res, context=context)

        return {'type': 'ir.actions.act_window_close'}

school_enrolment_invoice()


class school_academic_period_new(osv.osv_memory):
    """
    This wizard creates a new year (school.academic.period) from the current one
    """

    _name = "school.academic.period.new"
    _description = "Create new Academic period"

    _columns = {
        'name': fields.char('Name', size=255, required=True),
    }

    def create_period(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        per_obj = pool_obj.get('school.academic.period')
        class_obj = pool_obj.get('school.class')
        per = per_obj.browse(cr, uid, context.get('active_id'), context=context)
        # create a new period from dialog data
        context.update({
            'name': self.browse(cr, uid, ids)[0].name,
        })
        new_per_id = per_obj.copy(cr, uid, per.id, context=context)
        # make ourself a copy of classes in previous year
        ctx = {'default_year_id': new_per_id}
        for sclass in per.class_ids:
            class_obj.copy(cr, uid, sclass.id, context=ctx)
        # now close previous year
        per_obj.archive_year(cr, uid, [per.id], context=context)
        return {'type': 'ir.actions.act_window_close'}

school_academic_period_new()


class school_enrolment_promote(osv.osv_memory):
    """
    This wizard promotes the current enrolment
    """

    _name = "school.enrolment.promote"
    _description = "Promote student"

    def _default_class_id(self, cr, uid, context=None):
        return resolve_id_from_context('class_id', context)

    def onchange_current_class_id(self, cr, uid, ids, class_id, ctx=None):
        sclass = self.pool.get('school.class').browse(
            cr,
            uid,
            class_id, context=ctx)
        if sclass:
            return {'value': {'promotion_idx': sclass.level_id.promotion_idx + 1 }}

    _columns = {
        'current_class_id': fields.many2one(
            'school.class',
            'Current class',
            required=True),
        'promotion_idx': fields.integer('Promotion index'),
        'class_id': fields.many2one(
            'school.class',
            'Applicable classes',
            required=True),
    }

    _defaults = {
        'current_class_id': _default_class_id,
    }

    def promote(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        enr_obj = pool_obj.get('school.enrolment')
        enr = enr_obj.browse(cr, uid, context.get('active_id'), context=context)

        context.update({
            'class_id': self.browse(cr, uid, ids)[0].class_id.id,
        })
        new_enr_id = enr_obj.copy(cr, uid, enr.id, context=context)
        # archive if need be
        if enr.state != 'archived':
            enr_obj.enrolment_archive(cr, uid, [enr.id], context=context)

        return {'type': 'ir.actions.act_window_close'}

school_enrolment_promote()


class school_class_promote(osv.osv_memory):
    """
    This wizard promotes all students in current class
    """

    _name = "school.class.promote"
    _description = "Promote class"

    def _default_class_id(self, cr, uid, context=None):
        return context.get('active_id')

    def _default_promotion_idx(self, cr, uid, context=None):
        sclass = self.pool.get('school.class').browse(
            cr,
            uid,
            context.get('active_id'),
            context=context)
        return sclass.level_id.promotion_idx + 1

    _columns = {
        'current_class_id': fields.many2one(
            'school.class',
            'Current class',
            required=True),
        'promotion_idx': fields.integer('Promotion index'),
        'class_id': fields.many2one(
            'school.class',
            'Applicable classes',
            required=True),
        'enrolment_ids': fields.many2many(
            'school.enrolment',
            'wizard_enrolment_rel',
            'wizard_id',
            'enrolment_id',
            'Students'),
    }

    _defaults = {
        'current_class_id': _default_class_id,
        'promotion_idx': _default_promotion_idx,
    }

    def promote(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        class_obj = pool_obj.get('school.class')
        enr_obj = pool_obj.get('school.enrolment')
        sclass = class_obj.browse(cr, uid, context.get('active_id'), context=context)

        context.update({
            'class_id': self.browse(cr, uid, ids)[0].class_id.id,
        })
        for enr in self.browse(cr, uid, ids)[0].enrolment_ids:
            new_enr_id = enr_obj.copy(cr, uid, enr.id, context=context)
            # archive if need be
        if sclass.state != 'archived':
            class_obj.archive_class(cr, uid, [sclass.id], context=context)

        return {'type': 'ir.actions.act_window_close'}

school_class_promote()
