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

class school_student_enrolment_checklist(osv.osv):
    _name = 'school.enrolment.checklist'

    def _default_enrolment_id(self, cr, uid, context=None):
        return resolve_id_from_context('enrolment_id', context)

    _columns = {
        'enrolment_id': fields.many2one(
            'school.enrolment',
            'enrolment',
            required=True,
            ondelete='cascade'),
        'item_id': fields.many2one('school.checklist.item', 'Required', required=True),
        'done': fields.boolean('Done'),
    }
    _defaults = {
        'enrolment_id':_default_enrolment_id,
    }

school_student_enrolment_checklist()

class school_enrolment(osv.osv):
    _name = 'school.enrolment'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Student enrolment for a specific Class'
    _track = {
        'state': {
            'school.mt_enrolment_enrolled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'enrolled',
            'school.mt_enrolment_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
    }

    def _default_student_id(self, cr, uid, context=None):
        return resolve_id_from_context('student_id', context)

    def _default_class_id(self, cr, uid, context=None):
        return resolve_id_from_context('class_id', context)

    def _default_checklist(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_enrolment_checklist_id:
            return user.company_id.default_enrolment_checklist_id.id
        return False

    def onchange_class_id(self, cr, uid, ids, class_id,
                        context=None):
        class_obj = self.pool.get('school.class')
        prod_id = False
        if class_id:
            sclass = class_obj.browse(
                cr,
                uid,
                class_id,
                context=context)
            if sclass.level_id.tuition_fee_id:
                prod_id = sclass.level_id.tuition_fee_id.id
        return {'value': {'tuition_fee_id': prod_id}}

    def onchange_checklist_id(self, cr, uid, ids, checklist_id,
                        context=None):
        chkitem_obj = self.pool.get('school.checklist.item')
        chk_ids = []
        if checklist_id:
            item_ids = chkitem_obj.search(
                cr,
                uid,
                [('checklist_id','=', checklist_id)],
                context=context)
            chk_ids = [{'item_id': i} for i in item_ids]
        return {'value': {'checklist_ids': chk_ids}}

    _columns = {
        'name': fields.related(
            'student_id',
            'name',
            type='char',
            relation='school.student',
            string="Student Name"),
        'student_id': fields.many2one(
            'school.student',
            'Student',
            required=True,
            ondelete='cascade',
            domain=[('state','=', 'student'),('current_class_id','=', None)]),
        'class_id': fields.many2one(
            'school.class',
            'Class',
            domain=[('state','=', 'open')],
            required=True),
        'class_state': fields.related(
            'class_id',
            'state',
            type='selection',
            relation='school.class',
            string="Class status"),
        'user_id': fields.many2one('res.users', 'Created By', required=True),
        'year_id': fields.related(
            'class_id',
            'year_id',
            type="many2one",
            relation='school.academic.period',
            string="Academic period"),
        'teacher_id': fields.related(
            'class_id',
            'teacher_id',
            type="many2one",
            relation='school.teacher',
            string="Class Teacher"),
        # financial
        'waive_tuition_fee': fields.boolean(
            'Waive tuition fee',
            help="Allow the enrolment to proceed without paying the fee."),
        'tuition_fee_id': fields.many2one(
            'product.product',
            'Tuition Fee'),
        'is_invoiced': fields.boolean(
            'Invoice generated'),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Tuition invoice',
            readonly=True),
        'invoice_state': fields.related(
            'invoice_id',
            'state',
            type='char',
            string="Invoice status",
            readonly=True),
        'enrolment_checklist_id': fields.many2one(
            'school.checklist',
            'Checklist',
            readonly=True,
            states={'draft': [('readonly', False)]}),
        'checklist_ids': fields.one2many(
            'school.enrolment.checklist',
            'enrolment_id',
            'Checklist Items'),
        'user_valid': fields.many2one(
            'res.users',
            'Validated By',
            readonly=True),
        'date': fields.date('Creation Date', required=True),
        'date_valid': fields.date('Validation Date', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('enrolled', 'Enrolled'),
            ('archived', 'Archived'),],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="Gives the status of the enrolment" ),
    }
    _defaults = {
        'date': fields.date.context_today,
        'student_id': _default_student_id,
        'class_id': _default_class_id,
        'enrolment_checklist_id': _default_checklist,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }
    _sql_constraints = [(
        'student_enrolment_unique',
        'unique (student_id, class_id)',
        'Class must be unique per Student !'),
    ]

    def create(self, cr, uid, vals, context=None):
        class_obj = self.pool.get('school.class')
        sclass = class_obj.browse(cr, uid, vals['class_id'], context=context)
        # assert only enrolment to current class
        if sclass.state == 'closed':
            raise osv.except_osv(
                _('Error!'),
                _('This class is already archived'))
        student_obj = self.pool.get('school.student')
        student = student_obj.browse(cr, uid, vals['student_id'], context=context)
        if student.current_class_id:
            raise osv.except_osv(
                _('Duplicate Error!'),
                _("This student is currently enrolled in '%s'" % student.current_class_id.name ))
        if student.invoice_id and student.invoice_id.state in ['draft', 'open']:
            raise osv.except_osv(
                _('Unpaid Error!'),
                _("Registration invoice '%s' is still pending." % student.invoice_id.number ))
        student_obj.write(
                cr,
                uid,
                [vals['student_id']],
                {'is_enrolled': True},
                context=context)
        return super(school_enrolment, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        student_obj = self.pool.get('school.student')
        """Allows to delete sales order lines in draft,cancel states"""
        for rec in self.browse(cr, uid, ids, context=context):
            student_obj.write(cr, uid, [rec.student_id.id], {'current_class_id': None}, context=context)
        return super(school_enrolment, self).unlink(cr, uid, ids, context=context)

    def enrolment_draft(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for enrolment in self.browse(cr, uid, ids):
            wf_service.trg_delete(uid, 'school.enrolment', enrolment.id, cr)
            wf_service.trg_create(uid, 'school.enrolment', enrolment.id, cr)
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def enrolment_validate(self, cr, uid, ids, context=None):
        self.validate_enrolment(cr, uid, ids, context)
        student_obj = self.pool.get('school.student')
        for enrolment in self.browse(cr, uid, ids, context=context):
            student_obj.write(
                cr,
                uid,
                std_ids,
                {'current_class_id': enrolment.class_id.id, 'is_enrolled': True},
                context=context)
        return self.write(
            cr,
            uid,
            ids,
            {
                'state': 'enrolled',
                'date_valid': time.strftime('%Y-%m-%d'),
                'user_valid': uid},
            context=context)

    def enrolment_cancel(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        inv_ids = [ enrolment.invoice_id.id for enrolment in self.browse(cr, uid, ids, context=context)
                        if enrolment.invoice_id]
        student_obj = self.pool.get('school.student')
        std_ids = [ enrolment.student_id.id for enrolment in self.browse(cr, uid, ids, context=context) ]
        student_obj.write(
            cr,
            uid,
            std_ids,
            {'current_class_id': None, 'is_enrolled': False},
            context=context)
        if inv_ids:
            inv_obj.action_cancel(cr, uid, inv_ids, context)
            inv_obj.action_cancel_draft(cr, uid, inv_ids, context)
            try:
                inv_obj.unlink(cr, uid, inv_ids, context=context)
            except:
                pass
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'cancel', 'invoice_id': None, 'is_invoiced': False},
            context=context)

    def validate_enrolment(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for enrolment in self.browse(cr, uid, ids, context=context):
            if not enrolment.waive_tuition_fee:
                if not enrolment.invoice_id:
                    raise osv.except_osv(
                        _('No Invoice!'),
                        _("Tuition hasn't been invoiced"))
            for check in enrolment.checklist_ids:
                if not check.done:
                    raise osv.except_osv(
                        _('Validation error!'),
                        _("Please verify '%s'" % check.item_id.name))

    def generate_invoice(self, cr, uid, ids, context):
        if not context:
            context = {}
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})

        for enr in self.browse(cr, uid, ids, context=ctx):
            if not enr.student_id.invoice_id:
                if not enr.student_id.waive_registration_fee:
                    student_obj.generate_invoice(
                        cr,
                        uid,
                        [enr.student_id.id],
                        context=context)
            if enr.waive_tuition_fee:
                raise osv.except_osv(
                    _('Cannot generate tuition invoice!'),
                    _("Tuition fees have been waived."))
            if not enr.tuition_fee_id:
                raise osv.except_osv(
                    _("Can't generate invoice"),
                    _("No tuition fee found."))
            if enr.invoice_id:
                raise osv.except_osv(
                    _('Invoice Already Generated!'),
                    _("Please refer to the linked Tuition Invoice"))

            inv_id = generic_generate_invoice(
                cr,
                uid,
                enr.tuition_fee_id.id,
                enr.student_id.billing_partner_id.id,
                enr.student_id.name,
                "Tuition Fee",
                ctx)

            self.write(cr, uid, [enr.id], {'invoice_id': inv_id, 'is_invoiced': True}, context=ctx)

        return True

school_enrolment()


class school_student(osv.osv):
    _name = 'school.student'
    _inherit = 'school.student'
    _columns = {
        'enrolment_ids': fields.one2many(
            'school.enrolment',
            'student_id',
            'enrolment history'),
        'current_class_id': fields.many2one(
            'school.class',
            'Current class'),
        'is_enrolled': fields.boolean(
            'Currently enrolled'),
    }

    def student_cancel(self, cr, uid, ids, context=None):
        reg_obj = self.pool.get('school.enrolment')
        inv_obj = self.pool.get('account.invoice')
        for student in self.browse(cr, uid, ids, context=context):
            reg_ids = [ enr.id for enr in student.enrolment_ids]
            if reg_ids:
                reg_obj.enrolment_cancel(cr, uid, reg_ids, context)
                reg_obj.unlink(cr, uid, reg_ids, context)
        return super(school_student, self).student_cancel(cr, uid, ids, context=context)

    def enroll_student(self, cr, uid, ids, context=None):
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'school', 'view_school_enrolment_form')

        student_obj = self.pool.get('school.student')
        student = student_obj.browse(cr, uid, context['student_id'], context=context)
        if student.is_enrolled:
            raise osv.except_osv(
                _('Duplicate Error!'),
                _("It seems an enrolment has already been created for %s.\nPlease check the draft enrolments." % student.name ))
        if not student.waive_registration_fee:
            if not student.invoice_id:
                raise osv.except_osv(
                    _('No Invoice!'),
                    _("No invoice has been generated"))
        if student.current_class_id:
            raise osv.except_osv(
                _('Duplicate Error!'),
                _("This student is currently enrolled in '%s'" % student.current_class_id.name ))
        if student.invoice_id and student.invoice_id.state in ['draft', 'open']:
            raise osv.except_osv(
                _('Unpaid Error!'),
                _("Registration invoice '%s' is still pending." % student.invoice_id.number ))

        return {
            'name': _("Enroll Student"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'school.enrolment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'domain': '[]',
            'context': context
        }

school_student()
