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

DRAFT = 'draft'
ENROLLED = 'enrolled'
CANCELLED = 'cancel'
ARCHIVED = 'archived'
CLOSED = 'closed'
INTERRUPT = 'interrupted'


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
    _description = 'Student enrolment'
    _order = "name"
    _track = {
        'state': {
            'school.mt_enrolment_enrolled': lambda self, cr, uid, obj, ctx=None: obj['state'] == ENROLLED,
            'school.mt_enrolment_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == CANCELLED,
        },
    }

    def _default_student_id(self, cr, uid, context=None):
        if not context:
            context = {}
        return resolve_id_from_context('student_id', context)

    def _default_class_id(self, cr, uid, context=None):
        if not context:
            context = {}
        return resolve_id_from_context('class_id', context)

    def _default_checklist(self, cr, uid, context=None):
        if not context:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_enrolment_checklist_id:
            return user.company_id.default_enrolment_checklist_id.id
        return False

    def onchange_class_id(self, cr, uid, ids, class_id, context=None):
        if not context:
            context = {}
        class_obj = self.pool.get('school.class')
        product_id = False
        if class_id:
            year_class = class_obj.browse(
                cr,
                uid,
                class_id,
                context=context)
            if year_class and year_class.level_id.tuition_fee_id:
                product_id = year_class.level_id.tuition_fee_id.id
        return {'value': {'tuition_fee_id': product_id}}

    def onchange_checklist_id(self, cr, uid, ids, checklist_id, context=None):
        if not context:
            context = {}
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
            string="Student Name",
            store=True),
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
            'Tuition Fee',
            domain=[('sale_ok','=',True)]),
        'is_invoiced': fields.boolean(
            'Invoice generated'),
        'invoice_id': fields.many2one(
            'account.invoice',
            'Tuition invoice',
            readonly=True,
            ondelete='cascade'),
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
            states={DRAFT: [('readonly', False)]}),
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
            (DRAFT, 'Draft'),
            (CANCELLED, 'Cancelled'),
            (ENROLLED, 'Enrolled'),
            (INTERRUPT, 'Interrupted'),
            (ARCHIVED, 'Archived'),],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="Gives the status of the enrolment"),
    }

    _defaults = {
        'date': fields.date.context_today,
        'student_id': _default_student_id,
        'class_id': _default_class_id,
        'enrolment_checklist_id': _default_checklist,
        'state': DRAFT,
        'user_id': lambda cr, uid, id, c={}: id,
    }

    _sql_constraints = [(
        'student_enrolment_unique',
        'unique (student_id, class_id)',
        'Class must be unique per Student !'),
    ]

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        class_obj = self.pool.get('school.class')
        year_class = class_obj.browse(cr, uid, vals['class_id'], context=context)
        # assert only enrolment to current class
        if year_class and year_class.state in [CLOSED, ARCHIVED]:
            raise osv.except_osv(
                _('Error!'),
                _('This class is not open for enrolments'))
        student_obj = self.pool.get('school.student')
        student = student_obj.browse(cr, uid, vals['student_id'], context=context)
        if student and student.current_class_id:
            raise osv.except_osv(
                _('Duplicate Error for %s!' % student.name),
                _("This student is currently enrolled in '%s'" % student.current_class_id.name ))
        if student.invoice_id and student.invoice_id.state in [DRAFT, 'open']:
            raise osv.except_osv(
                _('Unpaid Error!'),
                _("Registration invoice '%s' is still pending." % student.invoice_id.number ))
        return super(school_enrolment, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, enr_id, default=None, context=None):
        if not context:
            context = {}
        if not default:
            default = {}
        enrolment = self.browse(cr, uid, enr_id, context=context)
        class_id = resolve_id_from_context('class_id', context)
        product_id = self.onchange_class_id(
                cr,
                uid,
                None,
                class_id,
                context=context)['value']['tuition_fee_id']
        checklist_ids = self.onchange_checklist_id(
                cr,
                uid,
                None,
                enrolment.enrolment_checklist_id.id,
                context=context)['value']['checklist_ids']

        default.update({
            'date': time.strftime('%Y-%m-%d'),
            'state':DRAFT,
            'user_id': uid,
            'class_id': class_id,
            'tuition_fee_id': product_id,
            'invoice_id': None,
            'user_valid': None,
            'date_valid': None,
            'is_invoiced': False,
            'checklist_ids': checklist_ids,
        })
        new_id = super(school_enrolment, self).copy(cr, uid, enr_id, default, context=context)
        return new_id

    def unlink(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        for record in self.browse(cr, uid, ids, context=context):
            if record.state not in [DRAFT,CANCELLED]:
                raise osv.except_osv(
                    _('Active enrolment!'),
                    _("You must either cancel or reset to draft to be able to delete."))
        return super(school_enrolment, self).unlink(cr, uid, ids, context=context)

    def enrolment_draft(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if not context:
            context = {}
        for enrolment in self.browse(cr, uid, ids):
            wf_service.trg_delete(uid, 'school.enrolment', enrolment.id, cr)
            wf_service.trg_create(uid, 'school.enrolment', enrolment.id, cr)
        return self.write(cr, uid, ids, {'state': DRAFT}, context=context)

    def enrolment_validate(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if not context:
            context = {}
        self.validate_enrolment(cr, uid, ids, context)
        student_obj = self.pool.get('school.student')
        for enrolment in self.browse(cr, uid, ids, context=context):
            wf_service.trg_validate(uid, 'school.student', enrolment.student_id.id, 'enroll', cr)
            student_obj.write(
                cr,
                uid,
                [enrolment.student_id.id],
                {'current_class_id': enrolment.class_id.id},
                context=context)
        return self.write(
            cr,
            uid,
            ids,
            {
                'state': ENROLLED,
                'date_valid': time.strftime('%Y-%m-%d'),
                'user_valid': uid
            },
            context=context)

    def enrolment_archive(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if not context:
            context = {}
        for enrolment in self.browse(cr, uid, ids, context=context):
            if context.get('skip_deroll', False) is False:
                _logger.error("running workflow trigger deroll")
                wf_service.trg_validate(uid, 'school.student', enrolment.student_id.id, 'deroll', cr)
        return self.write(
            cr,
            uid,
            ids,
            {'state': ARCHIVED},
            context=context)

    def enrolment_interrupt(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        item_ids = self.search(
            cr,
            uid,
            [('state','=', ENROLLED), ('id', 'in', ids)],
            context=context)
        return self.write(
            cr,
            uid,
            item_ids,
            {'state': INTERRUPT},
            context=context)

    def enrolment_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if not context:
            context = {}
        inv_obj = self.pool.get('account.invoice')
        return_ids = []
        for enrolment in self.browse(cr, uid, ids, context=context):
            vals = {'state': CANCELLED}
            if 'skip_deroll' in context:
                _logger.debug("running workflow trigger deroll")
                wf_service.trg_validate(uid, 'school.student', enrolment.student_id.id, 'deroll', cr)
            if enrolment.invoice_id:
                # if possible, delete invoice
                try:
                    inv_obj.action_cancel(cr, uid, [enrolment.invoice_id.id], context)
                    inv_obj.action_cancel_draft(cr, uid, [enrolment.invoice_id.id], context)
                    inv_obj.unlink(cr, uid, [enrolment.invoice_id.id], context=context)
                    vals['invoice_id'] = None
                    vals['is_invoiced'] = False
                except Exception:
                    pass
            return_ids.append(
                self.write(
                    cr,
                    uid,
                    ids,
                    vals,
                    context=context))
        return return_ids

    def validate_enrolment(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        for enrolment in self.browse(cr, uid, ids, context=context):
            if not enrolment.waive_tuition_fee:
                if not enrolment.invoice_id:
                    raise osv.except_osv(
                        _('No Invoice!'),
                        _("Tuition hasn't been invoiced"))
            if enrolment.invoice_id and enrolment.invoice_id.state == DRAFT:
                raise osv.except_osv(
                    _('No validated invoice'),
                    _("Tuition invoice hasn't been validated"))
            for check in enrolment.checklist_ids:
                if not check.done:
                    raise osv.except_osv(
                        _('Validation error!'),
                        _("Please verify '{0}'").format(check.item_id.name))

    def action_generate_invoice(self, cr, uid, ids, context):
        if not context:
            context = {}
        ctx = context.copy()
        ctx.update({'account_period_prefer_normal': True})

        for enrolment in self.browse(cr, uid, ids, context=ctx):
            if enrolment.waive_tuition_fee:
                raise osv.except_osv(
                    _('Cannot generate tuition invoice!'),
                    _("Tuition fees have been waived."))
            if not enrolment.tuition_fee_id:
                raise osv.except_osv(
                    _("Can't generate invoice"),
                    _("No tuition fee found."))
            if enrolment.invoice_id:
                raise osv.except_osv(
                    _('Invoice Already Generated!'),
                    _("Please refer to the linked Tuition Invoice"))

            invoice_id = generic_generate_invoice(
                cr,
                uid,
                enrolment.tuition_fee_id.id,
                enrolment.student_id.billing_partner_id.id,
                enrolment.student_id.name,
                "Tuition Fee",
                ctx)

            self.write(cr, uid, [enrolment.id], {'invoice_id': invoice_id, 'is_invoiced': True}, context=ctx)

        return True

    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given enrolments. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [so.invoice_id.id]
        #choose the view_mode accordingly
        if len(inv_ids) > 1:
            result['domain'] = "[('id','in',[{}])]".format(','.join(map(str, inv_ids)))
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result

school_enrolment()


class school_student(osv.osv):
    _name = 'school.student'
    _inherit = 'school.student'
    _columns = {
        'enrolment_ids': fields.one2many(
            'school.enrolment',
            'student_id',
            'enrolment history'),
        'is_enrolled': fields.boolean(
            'obsolete field'),
        'current_class_id': fields.many2one(
            'school.class',
            'Current class'),
	}

    def copy(self, cr, uid, student_id, default=None, context=None):
        if not context:
            context = {}
        if not default:
            default = {}
        default.update({
            'current_class_id':False,
            'enrolment_ids':[],
            'is_enrolled': False,
        })

        new_id = super(school_student, self).copy(cr, uid, student_id, default, context=context)
        return new_id

    def student_validate(self, cr, uid, ids, context=None):
        _logger.debug("running overloaded student_validate")
        if not context:
            context = {}
        self.write(
            cr,
            uid,
            ids,
            {
                'current_class_id': False,
                'is_enrolled': False,
            },
            context=context)
        return super(school_student, self).student_validate(cr, uid, ids, context=context)

    def student_draft(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        self.write(
            cr,
            uid,
            ids,
            {
                'current_class_id': False,
                'is_enrolled': False,
            },
            context=context)
        return super(school_student, self).student_draft(cr, uid, ids, context=context)


    def student_cancel(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        enr_obj = self.pool.get('school.enrolment')
        for student in self.browse(cr, uid, ids, context=context):
            enr_ids = [ enrolment.id for enrolment in student.enrolment_ids if enrolment.state == ENROLLED]
            if enr_ids:
                enr_obj.enrolment_cancel(cr, uid, enr_ids, context)
                enr_obj.unlink(cr, uid, enr_ids, context)
        return super(school_student, self).student_cancel(cr, uid, ids, context=context)

    def student_suspend(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        enr_obj = self.pool.get('school.enrolment')
        for student in self.browse(cr, uid, ids, context=context):
            enr_ids = [ enrolment.id for enrolment in student.enrolment_ids if enrolment.state == ENROLLED]
            if enr_ids:
                ctx = context.copy()
                ctx['skip_deroll'] = True
                enr_obj.enrolment_interrupt(cr, uid, enr_ids, ctx)
        self.write(
            cr,
            uid,
            ids,
            {'current_class_id': False},
            context=context)
        return super(school_student, self).student_suspend(cr, uid, ids, context=context)

    def enroll_student(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'school', 'view_school_enrolment_form')

        student_obj = self.pool.get('school.student')
        student = student_obj.browse(cr, uid, context['student_id'], context=context)
        if student.state == ENROLLED:
            raise osv.except_osv(
                _('Duplicate Error!'),
                _("It seems an enrolment has already been created for {0}.\nPlease check the draft enrolments.").format(student.name))
        if not student.waive_registration_fee:
            if not student.invoice_id:
                raise osv.except_osv(
                    _('No Invoice!'),
                    _("No invoice has been generated"))
        if student.current_class_id:
            raise osv.except_osv(
                _('Duplicate Error!'),
                _("This student is currently enrolled in '{0}'").format(student.current_class_id.name))
        if student.invoice_id and student.invoice_id.state in [DRAFT, 'open']:
            raise osv.except_osv(
                _('Unpaid Error!'),
                _("Registration invoice '{0}' is still pending.").format(student.invoice_id.number))

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
