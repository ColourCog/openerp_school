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


class school_student(osv.osv):
    _name = 'school.student'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Student'
    _track = {
        'state': {
            'school.mt_student_student': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'student',
            'school.mt_student_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
    }

    def _default_enrolment_fee(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_enrolment_fee_id:
            return user.company_id.default_enrolment_fee_id.id
        return False

    _columns = {
        'name': fields.char('Student Name', size=255, select=True, readonly=True),
        'surname': fields.char('Family Name', size=255, required=True),
        'firstname': fields.char('First Name(s)', size=255, required=True),
        'gender': fields.selection([
            ('male', 'Male'),
            ('female', 'Female'),
            ],
            'Gender',
            required=True,
            selec=True),
        'birthday': fields.date('Date of birth', required=True),
        'birthplace': fields.char('Place of birth', size=255),
        'nationality_id': fields.many2one('res.country', 'Nationality'),
        'nationality_ids': fields.many2many(
            'res.country',
            'student_country_rel',
            'student_id',
            'country_id',
            'Other Nationalities'),
        'religion_id': fields.many2one('school.religion', 'Family Religion'),
        'language_id': fields.many2one('school.language', 'First Language'),
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
        'previous_ids': fields.one2many(
            'school.student.education',
            'student_id',
            'Previous Schools'),
        'billing_partner_id': fields.many2one(
            'res.partner',
            'Bill to',
            required=True,
            domain=[('customer','=',True)]),
        'enrolment_fee_id': fields.many2one('product.product', 'Enrolment Fee', required=True),
        'waive_fee': fields.boolean(
            'Waive Fee ?',
            help="Allow the Enrolment to proceed without paying the fee."),
        'reference': fields.char(
            'Payment reference',
            size=64,
            help="Check number, or short memo"),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Enrolment Invoice',
            readonly=True,
            ),
        'invoice_state': fields.related(
            'invoice_id',
            'state',
            type='char',
            string="Invoice status"),
        'birth_certificate': fields.boolean(
            'Birth certificate ?',
            help="Check if birth certificate was provided."),
        'vaccination': fields.boolean(
            'Vaccination card ?',
            help="Check if vaccination card was provided."),
        'education_report': fields.boolean(
            'Previous school reports ?',
            help="Check if last school's reports were provided."),
        'user_id': fields.many2one('res.users', 'Created By', required=True),
        'user_valid': fields.many2one(
            'res.users',
            'Validated By',
            readonly=True),
        'date': fields.date('Creation Date', required=True),
        'date_valid': fields.date('Validation Date', readonly=True),
        'state': fields.selection([
            ('draft', 'Enrolment'),
            ('cancel', 'Cancelled'),
            ('suspend', 'Inactive'),
            ('student', 'Student')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="Gives the status of the enrolment or studen." ),
    }

    _defaults = {
        'enrolment_fee_id': _default_enrolment_fee,
        'date': fields.date.context_today,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }


    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = ' '.join([vals.get('surname').upper(), vals.get('firstname').capitalize()])
        if not vals.get('user_id'):
            vals['user_id'] = uid
        return super(school_student, self).create(cr, uid, vals, context=context)

    def student_draft(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for student in self.browse(cr, uid, ids):
            wf_service.trg_delete(uid, 'school.student', student.id, cr)
            wf_service.trg_create(uid, 'school.student', student.id, cr)
        return self.write(cr, uid, ids, {'state': 'draft', 'date_valid': None, 'user_valid': None}, context=context)

    def student_validate(self, cr, uid, ids, context=None):
        self.validate_enrolment(cr, uid, ids, context)
        return self.write(
            cr,
            uid,
            ids,
            {
                'state': 'student',
                'date_valid': time.strftime('%Y-%m-%d'),
                'user_valid': uid},
            context=context)

    def student_suspend(self, cr, uid, ids, context=None):
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'suspend'},
            context=context)

    def student_resume(self, cr, uid, ids, context=None):
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'student'},
            context=context)

    def student_cancel(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        voucher_obj = self.pool.get('account.voucher')
        for student in self.browse(cr, uid, ids, context=context):
            if student.invoice_id:
                inv_obj.action_cancel(cr, uid, [student.invoice_id.id], context)
                inv_obj.action_cancel_draft(cr, uid, [student.invoice_id.id], context)
                try:
                    inv_obj.unlink(cr, uid, [student.invoice_id.id], context=context)
                except:
                    pass
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'cancel', 'invoice_id': None},
            context=context)

    def validate_enrolment(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for student in self.browse(cr, uid, ids, context=context):
            if not student.waive_fee:
                if not student.reference:
                    raise osv.except_osv(
                        _('Payment Reference Missing!'),
                        _("Cannot validate unpaid Enrolment fee"))
            if not student.birth_certificate:
                raise osv.except_osv(
                    _('No Birth Certificate!'),
                    _('Birth Certificate must have been provided'))
            if not student.vaccination:
                raise osv.except_osv(
                    _('No Vaccination!'),
                    _('Proof of Vaccination must have been provided'))
            if not student.education_report:
                raise osv.except_osv(
                    _('No School Report!'),
                    _('Previous School reports must have been provided'))

    def generate_invoice(self, cr, uid, ids, context):
        if not context:
            context = {}
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        period_obj = self.pool.get('account.period')
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        total = 0.0
        for student in self.browse(cr, uid, ids, context=ctx):
            if student.waive_fee:
                raise osv.except_osv(
                    _('Cannot generate Enrolment invoice!'),
                    _("Enrolment Fees have been waived."))
            if student.invoice_id:
                raise osv.except_osv(
                    _('Invoice Already Generated!'),
                    _("Please refer to the linked Enrolment Invoice"))

            line = {
                'name': student.enrolment_fee_id.name,
                'product_id': student.enrolment_fee_id.id,
                'quantity': 1,
                }
            # run inv_line_obj's onchange to update
            n = inv_line_obj.product_id_change(
                cr,
                uid,
                ids,
                student.enrolment_fee_id.id,
                student.enrolment_fee_id.uom_id.id,
                qty=1,
                name='',
                type='out_invoice',
                partner_id=student.billing_partner_id.id,
                company_id=None,
                context=None)['value']
            line.update(n)

            inv_line = (0, 0, line)

            invoice = {
                'type': 'out_invoice',
                'name': " ".join([student.name, "Enrolment Fee"]),
                'partner_id': student.billing_partner_id.id,
                'invoice_line': [inv_line],
                }
            # run inv_obj's onchange to update
            n = inv_obj.onchange_partner_id(
                cr,
                uid,
                ids,
                'out_invoice',
                student.billing_partner_id.id,
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

            self.write(cr, uid, [student.id], {'invoice_id': inv_id}, context=ctx)

        return True

    def pay_invoice(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')

        student = self.browse(cr, uid, ids[0], context=context)
        if not student.invoice_id:
            raise osv.except_osv(
                _('No Invoice!'),
                _('Generate an invoice to pay.'))

        inv_obj = self.pool.get('account.invoice')
        inv = inv_obj.browse(cr, uid, student.invoice_id.id, context=context)
        if not inv.residual:
            raise osv.except_osv(
                _('Invoice Already Paid!'),
                _('This invoice reports a null residual amount.'))

        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'default_reference': student.reference,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        if view_type == 'form':
            if not view_id and context.get('stage'):
                if context.get('stage') == 'enrolment':
                    result = mod_obj.get_object_reference(cr, uid, 'school', 'view_school_enrolment_form')
                    result = result and result[1] or False
                    view_id = result
        res = super(school_student, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        return res

school_student()
