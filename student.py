#/bin/env python2

## STUDENT
# The sudent database works like the sales database. The first stage
# of a student is an enrolment.
# A validated enrolment becomes a student.
# The views are the ones that make the difference; especially
# the fields_view_get

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
        'name': fields.char('Name', size=255),
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


class school_student_previous(osv.osv):
    _name = 'school.student.previous'

    _columns = {
        'name': fields.related(
            'school_id',
            'name',
            type='many2one',
            relation='school.school',
            string="School Name"),
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'school_id': fields.many2one('school.school', 'Previous School', required=True),
        'date_from': fields.date('From'),
        'date_to': fields.date('To'),

    }

school_student_previous()


class school_student_relative(osv.osv):
    _name = 'school.student.relative'

    _columns = {
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'partner_id': fields.many2one('res.partner', 'Relative', required=True),
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
            'school.student.previous',
            'student_id',
            'Previous Schools'),
        'billing_partner_id': fields.many2one('res.partner', 'Bill to', required=True),
        'enrolment_fee_id': fields.many2one('product.product', 'Enrolment Fee', required=True),
        'reference': fields.char(
            'Payment reference',
            size=64,
            help="Check number, or short memo",
            required=True),
        'birth_certificate': fields.boolean(
            'Birth certificate',
            help="Check if birth certificate was provided."),
        'vaccination': fields.boolean(
            'Vaccination card',
            help="Check if vaccination card was provided."),
        'previous_report': fields.boolean(
            'Previous school reports',
            help="Check if last school's reports were provided."),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'date': fields.date('Enrolment Date', required=True),
        'state': fields.selection([
            ('draft', 'Enrolment'),
            ('cancel', 'Cancelled'),
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
        return super(school_student, self).create(cr, uid, vals, context=context)

    def validate_enrolment(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        student = self.browse(cr, uid, ids[0], context=context)
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
        if not student.previous_report:
            raise osv.except_osv(
                _('No School Report!'),
                _('Previous School reports must have been provided'))


school_student()
