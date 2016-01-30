#/bin/env python2

## REGISTRATION

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
from tools import resolve_id_from_context
_logger = logging.getLogger(__name__)

class school_student__registration_checklist(osv.osv):
    _name = 'school.registration.checklist'

    def _default_registration_id(self, cr, uid, context=None):
        return resolve_id_from_context('registration_id', context)

    _columns = {
        'registration_id': fields.many2one(
            'school.registration',
            'Registration',
            required=True,
            ondelete='cascade'),
        'item_id': fields.many2one('school.checklist.item', 'Required', required=True),
        'done': fields.boolean('Done'),
    }
    _defaults = {
        'registration_id':_default_registration_id,
    }

school_student__registration_checklist()

class school_registration(osv.osv):
    _name = 'school.registration'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Student Registration for a specific Class'
    _track = {
        'state': {
            'school.mt_registration_registered': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'registered',
            'school.mt_registration_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
    }

    def _default_student_id(self, cr, uid, context=None):
        return resolve_id_from_context('student_id', context)

    def _default_class_id(self, cr, uid, context=None):
        return resolve_id_from_context('class_id', context)

    def _default_checklist(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_registration_checklist_id:
            return user.company_id.default_registration_checklist_id.id
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
        'name': fields.char('Registration No', size=255, required=True,),
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
            relation='school.academic.year',
            string="Year"),
        'tuition_fee_id': fields.many2one(
            'product.product',
            'Tuition Fee'),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Tuition Invoice',
            readonly=True),
        'invoice_state': fields.related(
            'invoice_id',
            'state',
            type='char',
            string="Invoice status",
            readonly=True),
        'registration_checklist_id': fields.many2one(
            'school.checklist',
            'Checklist',
            readonly=True,
            states={'draft': [('readonly', False)]}),
        'checklist_ids': fields.one2many(
            'school.registration.checklist',
            'registration_id',
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
            ('registered', 'Registered')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="Gives the status of the registration" ),
    }
    _defaults = {
        'name': "/",
        'date': fields.date.context_today,
        'student_id': _default_student_id,
        'class_id': _default_class_id,
        'registration_checklist_id': _default_checklist,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }
    _sql_constraints = [(
        'student_registration_unique',
        'unique (student_id, class_id)',
        'Class must be unique per Student !'),
    ]

    def create(self, cr, uid, vals, context=None):
        class_obj = self.pool.get('school.class')
        sclass = class_obj.browse(cr, uid, vals['class_id'], context=context)
        # assert only registration to current class
        if sclass.state == 'closed':
            raise osv.except_osv(
                _('Error!'),
                _('This class is already archived'))
        student_obj = self.pool.get('school.student')
        student = student_obj.browse(cr, uid, vals['student_id'], context=context)
        if student.current_class_id:
            raise osv.except_osv(
                _('Error!'),
                _("This student is currently registered in '%s'" % student.current_class_id.name ))
        student_obj.write(
            cr,
            uid,
            [vals['student_id']],
            {'current_class_id': vals['class_id']},
            context=context)
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'school.registration') or '/'
        return super(school_registration, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        student_obj = self.pool.get('school.student')
        """Allows to delete sales order lines in draft,cancel states"""
        for rec in self.browse(cr, uid, ids, context=context):
            student_obj.write(cr, uid, [rec.student_id.id], {'current_class_id': None}, context=context)
        return super(school_registration, self).unlink(cr, uid, ids, context=context)

    def registration_draft(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for registration in self.browse(cr, uid, ids):
            wf_service.trg_delete(uid, 'school.registration', registration.id, cr)
            wf_service.trg_create(uid, 'school.registration', registration.id, cr)
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def registration_validate(self, cr, uid, ids, context=None):
        self.validate_registration(cr, uid, ids, context)
        return self.write(
            cr,
            uid,
            ids,
            {
                'state': 'registered',
                'date_valid': time.strftime('%Y-%m-%d'),
                'user_valid': uid},
            context=context)

    def registration_cancel(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        std_ids = [ registration.invoice_id.id for registration in self.browse(cr, uid, ids, context=context)
                        if registration.invoice_id]
        if std_ids:
            inv_obj.action_cancel(cr, uid, std_ids, context)
            inv_obj.action_cancel_draft(cr, uid, std_ids, context)
            try:
                inv_obj.unlink(cr, uid, std_ids, context=context)
            except:
                pass
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'cancel', 'invoice_id': None},
            context=context)

    def validate_registration(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for registration in self.browse(cr, uid, ids, context=context):
            for check in registration.checklist_ids:
                if not check.done:
                    raise osv.except_osv(
                        _('Validation error!'),
                        _("Please verify '%s'" % check.item_id.name))

    def generate_invoice(self, cr, uid, ids, context):
        if not context:
            context = {}
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        student_obj = self.pool.get('school.student')
        period_obj = self.pool.get('account.period')
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        total = 0.0
        for reg in self.browse(cr, uid, ids, context=ctx):
            if not reg.student_id.invoice_id:
                if not reg.student_id.waive_fee:
                    student_obj.generate_invoice(
                        cr,
                        uid,
                        [reg.student_id.id],
                        context=context)
            if not reg.tuition_fee_id:
                raise osv.except_osv(
                    _("Can't generate invoice"),
                    _("No tuition fee found."))
            if reg.invoice_id:
                raise osv.except_osv(
                    _('Invoice Already Generated!'),
                    _("Please refer to the linked Tuition Invoice"))

            line = {
                'name': reg.tuition_fee_id.name,
                'product_id': reg.tuition_fee_id.id,
                'quantity': 1,
                }
            # run inv_line_obj's onchange to update
            n = inv_line_obj.product_id_change(
                cr,
                uid,
                ids,
                reg.tuition_fee_id.id,
                reg.tuition_fee_id.uom_id.id,
                qty=1,
                name='',
                type='out_invoice',
                partner_id=reg.student_id.billing_partner_id.id,
                company_id=None,
                context=None)['value']
            line.update(n)

            inv_line = (0, 0, line)

            invoice = {
                'type': 'out_invoice',
                'name': " ".join([reg.student_id.name, "Tuition Fee"]),
                'partner_id': reg.student_id.billing_partner_id.id,
                'invoice_line': [inv_line],
                }
            # run inv_obj's onchange to update
            n = inv_obj.onchange_partner_id(
                cr,
                uid,
                ids,
                'out_invoice',
                reg.student_id.billing_partner_id.id,
                date_invoice=False,
                payment_term=False,
                partner_bank_id=False,
                company_id=False)['value']
            invoice.update(n)

            inv_id = inv_obj.create(cr, uid, invoice, context=ctx)
            inv_obj.action_date_assign(cr,uid,[inv_id],context)
            inv_obj.action_move_create(cr,uid,[inv_id],context=context)
            inv_obj.action_number(cr,uid,[inv_id],context)
            inv_obj.invoice_validate(cr,uid,[inv_id],context=context)

            self.write(cr, uid, [reg.id], {'invoice_id': inv_id}, context=ctx)

        return True

    def cancel_invoice(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        reg_ids = [ reg.invoice_id.id for reg in self.browse(cr, uid, ids, context=context)
                        if reg.invoice_id]
        if reg_ids:
            inv_obj.action_cancel(cr, uid, reg_ids, context)
            inv_obj.action_cancel_draft(cr, uid, reg_ids, context)
            try:
                inv_obj.unlink(cr, uid, reg_ids, context=context)
            except:
                pass
        return self.write( cr, uid, ids, {'invoice_id': None}, context=context)

school_registration()

class school_student(osv.osv):
    _name = 'school.student'
    _inherit = 'school.student'
    _columns = {
        'registration_ids': fields.one2many(
            'school.registration',
            'student_id',
            'Registration history'),
         'current_class_id': fields.many2one(
            'school.class',
            'Current class'),
    }

    def student_cancel(self, cr, uid, ids, context=None):
        reg_obj = self.pool.get('school.registration')
        inv_obj = self.pool.get('account.invoice')
        for student in self.browse(cr, uid, ids, context=context):
            reg_ids = [ reg.id for reg in student.registration_ids]
            if reg_ids:
                reg_obj.cancel_invoice(cr, uid, reg_ids, context)
        return super(school_student, self).student_cancel(cr, uid, ids, context=context)

school_student()
