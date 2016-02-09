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
from tools import generic_generate_invoice
_logger = logging.getLogger(__name__)

class school_student_checklist(osv.osv):
    _name = 'school.student.checklist'

    def _default_student_id(self, cr, uid, context=None):
        return resolve_id_from_context('student_id', context)

    _columns = {
        'student_id': fields.many2one(
            'school.student',
            'Student',
            required=True,
            ondelete='cascade'),
        'item_id': fields.many2one('school.checklist.item', 'Required', required=True),
        'done': fields.boolean('Done'),
    }
    _defaults = {
        'student_id':_default_student_id,
    }

school_student_checklist()


class school_student(osv.osv):
    # registration is a financial/administrative concept
    # We should split the financial side out to another module
    # maybe school.student.registration

    _name = 'school.student'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Student'
    _track = {
        'state': {
            'school.mt_student_student': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'student',
            'school.mt_student_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
    }

    def _default_registration_fee(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_registration_fee_id:
            return user.company_id.default_registration_fee_id.id
        return False

    def _default_checklist(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_registration_checklist_id:
            return user.company_id.default_registration_checklist_id.id
        return False

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
        #financial
        'registration_fee_id': fields.many2one('product.product', 'Registration fee', required=True),
        # financial
        'waive_fee': fields.boolean(
            'Waive registration fee',
            help="Allow the registration to proceed without paying the fee."),
        #financial
        'invoice_id': fields.many2one(
            'account.invoice',
            'Registration invoice',
            readonly=True,
            ),
        #financial
        'invoice_state': fields.related(
            'invoice_id',
            'state',
            type='char',
            string="Invoice status",
            readonly=True),
        'enrolement_checklist_id': fields.many2one(
            'school.checklist',
            'Checklist',
            readonly=True,
            states={'draft': [('readonly', False)]}),
        'checklist_ids': fields.one2many(
            'school.student.checklist',
            'student_id',
            'Checklist Items'),
        'reg_num': fields.char('Registration No', size=255),
        'user_id': fields.many2one('res.users', 'Created By', required=True),
        'user_valid': fields.many2one(
            'res.users',
            'Validated By',
            readonly=True),
        'date': fields.date('Creation Date', required=True),
        'date_valid': fields.date('Validation Date', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('suspend', 'Inactive'),
            ('student', 'Student')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="Gives the status of the registration" ),
    }

    _defaults = {
        'registration_fee_id': _default_registration_fee,
        'enrolement_checklist_id': _default_checklist,
        'date': fields.date.context_today,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }


    def create(self, cr, uid, vals, context=None):
        vals['firstname'] = vals.get('firstname').title()
        vals['surname'] = vals.get('surname').upper()
        if vals.get('reg_num', '/') == '/':
            vals['reg_num'] = self.pool.get('ir.sequence').get(cr, uid, 'school.registration')
        if vals.get('name', '/') == '/':
            vals['name'] = ' '.join([vals.get('surname'), vals.get('firstname')])
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
        self.validate_registration(cr, uid, ids, context)
        return self.write(
            cr,
            uid,
            ids,
            {
                'state': 'student',
                'date_valid': time.strftime('%Y-%m-%d'),
                'user_valid': uid},
            context=context)

    # custom
    def student_suspend(self, cr, uid, ids, context=None):
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'suspend'},
            context=context)

    # custom
    def student_resume(self, cr, uid, ids, context=None):
        return self.write(
            cr,
            uid,
            ids,
            {'state': 'student'},
            context=context)

    def student_cancel(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        std_ids = [ student.invoice_id.id for student in self.browse(cr, uid, ids, context=context)
                        if student.invoice_id]
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
        for student in self.browse(cr, uid, ids, context=context):
            for check in student.checklist_ids:
                if not check.done:
                    raise osv.except_osv(
                        _('Validation error!'),
                        _("Please verify '%s'" % check.item_id.name))

    def generate_invoice(self, cr, uid, ids, context):
        if not context:
            context = {}
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})
        for student in self.browse(cr, uid, ids, context=ctx):
            if student.waive_fee:
                raise osv.except_osv(
                    _('Cannot generate registration invoice!'),
                    _("registration Fees have been waived."))
            if student.invoice_id:
                raise osv.except_osv(
                    _('Invoice Already Generated!'),
                    _("Please refer to the linked registration Invoice"))

            inv_id = generic_generate_invoice(
                cr,
                uid,
                student.registration_fee_id.id,
                student.billing_partner_id.id,
                student.name,
                "Registration Fee",
                ctx)

            self.write(cr, uid, [student.id], {'invoice_id': inv_id}, context=ctx)

        return True


    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        if view_type == 'form':
            if not view_id and context.get('stage'):
                if context.get('stage') == 'registration':
                    result = mod_obj.get_object_reference(cr, uid, 'school', 'view_school_registration_form')
                    result = result and result[1] or False
                    view_id = result
        res = super(school_student, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        return res

school_student()
