#/bin/env python2

## REGISTRATION

import time
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_academic_year(osv.osv):
    _name = 'school.academic.year'
    _description = 'Academic Year'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'class_ids': fields.one2many(
            'school.class',
            'year_id',
            'Classes for this Year'),
        'state': fields.selection([
            ('open', 'Current'),
            ('closed', 'Archived')],
            'Status',
            readonly=True,
            track_visibility='onchange',
            select=True,
            help="The archive status of this Year" ),
    }
    _defaults = {
        'state': "open",
    }

    def close_year(self, cr, uid, ids, context=None):
        class_ids = []
        class_obj = self.pool.get('school.class')
        for year in self.browse(cr, uid, ids, context=context):
            class_ids.extend(
                class_obj.search(
                    cr,
                    uid,
                    [('year_id','=',year.id)],
                    context=context))
        class_obj.close_class(cr, uid, class_ids, context=context)
        self.write(cr, uid, ids, {'state': 'closed'}, context=context)

school_academic_year()

class school_academic_level(osv.osv):
    _name = 'school.academic.level'
    _description = 'Academic Level'

    _columns = {
        'name': fields.char('Name', size=255, required=True),
        'tuition_fee_id': fields.many2one(
            'product.product',
            'Default tuition Fee',
            required=True),
        'description': fields.text('Description'),
    }

school_academic_level()

class school_teacher(osv.osv):
    _name = 'school.teacher'
    _description = 'Teacher'

    _columns = {
        'name': fields.char('Teacher Name', size=255, select=True),
        'employee_id': fields.many2one(
            'hr.employee',
            'Employee'),
    }
    def create(self, cr, uid, vals, context=None):
        hr_obj = self.pool.get('hr.employee')
        if vals.get('name', '/') == '/':
            vals['name'] = 'Unnamed Teacher'
            if vals.get('employee_id', False):
                employee = hr_obj.browse(cr, uid, vals['employee_id'], context)
                vals['name'] = employee.name
        return super(school_teacher, self).create(cr, uid, vals, context=context)

school_teacher()


class school_class(osv.osv):
    _name = 'school.class'
    _description = 'Class'

    _columns = {
        'name': fields.char('Name', size=255, select=True),
        'year_id': fields.many2one(
            'school.academic.year',
            'Academic Year',
            required=True),
        'level_id': fields.many2one(
            'school.academic.level',
            'Year',
            required=True),
        'teacher_id': fields.many2one(
            'school.teacher',
            'Class (Homeroom) Teacher',
            required=True),
        'registration_ids': fields.one2many(
            'school.student.registration',
            'class_id',
            'Class Roll'),
        'state': fields.related(
            'year_id',
            'state',
            type='selection',
            relation='school.academic.year',
            string="Status"),
    }
    _sql_constraints = [(
        'level_year_unique',
        'unique (year_id, level_id)',
        'Level must be unique per Year !'),
    ]

    def create(self, cr, uid, vals, context=None):
        teacher_obj = self.pool.get('school.teacher')
        level_obj = self.pool.get('school.academic.level')
        year_obj = self.pool.get('school.academic.year')
        if vals.get('name', '/') == '/':
            teacher = teacher_obj.browse(cr, uid, vals['teacher_id'], context)
            level = level_obj.browse(cr, uid, vals['level_id'], context)
            year = year_obj.browse(cr, uid, vals['year_id'], context)
            vals['name'] = ' '.join([level.name, teacher.name, year.name])
        return super(school_class, self).create(cr, uid, vals, context=context)

    def close_class(self, cr, uid, ids, context=None):
        """Archives class and releases students for new registration"""
        student_ids = []
        for sclass in self.browse(cr, uid, ids, context=context):
            for reg in sclass.registration_ids:
                student_ids.append(reg.student_id.id)
        student_obj = self.pool.get('school.student')
        student_obj.write(cr, uid, student_ids, {'current_class_id': None}, context=context)
        self.write(cr, uid, ids, {'state': 'closed'}, context=context)

school_class()


class school_student_registration(osv.osv):
    _name = 'school.student.registration'
    _description = 'Student Registration'

    def _get_student(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('student_id', False)

    def _get_class(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('class_id', False)

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
            prod_id = sclass.level_id.tuition_fee_id.id
            return {'value': {'tuition_fee_id': prod_id}}

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
        'state': fields.related(
            'student_id',
            'state',
            type='selection',
            relation='school.student',
            string="Status"),
    }
    _defaults = {
        'name': "/",
        'student_id': _get_student,
        'class_id': _get_class,
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
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'school.student.registration') or '/'
        return super(school_student_registration, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        student_obj = self.pool.get('school.student')
        """Allows to delete sales order lines in draft,cancel states"""
        for rec in self.browse(cr, uid, ids, context=context):
            student_obj.write(cr, uid, [rec.student_id.id], {'current_class_id': None}, context=context)
        return super(school_student_registration, self).unlink(cr, uid, ids, context=context)

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

school_student_registration()

class school_student(osv.osv):
    _name = 'school.student'
    _inherit = 'school.student'
    _columns = {
        'registration_ids': fields.one2many(
            'school.student.registration',
            'student_id',
            'Registration history'),
         'current_class_id': fields.many2one(
            'school.class',
            'Current class'),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}

        if view_type == 'form':
            if not view_id and context.get('stage'):
                if context.get('stage') == 'academic':
                    result = mod_obj.get_object_reference(cr, uid, 'school', 'view_school_student_form')
                    result = result and result[1] or False
                    view_id = result
        res = super(school_student, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        return res

    def student_cancel(self, cr, uid, ids, context=None):
        reg_obj = self.pool.get('school.student.registration')
        inv_obj = self.pool.get('account.invoice')
        for student in self.browse(cr, uid, ids, context=context):
            reg_ids = [ reg.id for reg in student.registration_ids]
            if reg_ids:
                reg_obj.cancel_invoice(cr, uid, reg_ids, context)
        return super(school_student, self).student_cancel(cr, uid, ids, context=context)

school_student()
