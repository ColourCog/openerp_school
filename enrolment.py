#/bin/env python2

import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_roster_extra(osv.osv):
    _name = 'school.roster.extra'
    _description = 'Enrolment Extra-curicular'

school_roster_enrolment()

class school_roster_enrolment(osv.osv):
    _name = 'school.roster.enrolment'
    _description = 'Roster Enrolment'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
          'school_roster_enrolment.mt_reg_accepted': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'accepted',
          'school_roster_enrolment.mt_reg_cancelled': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancelled',
          'school_roster_enrolment.mt_reg_pending': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'pending',
          'school_roster_enrolment.mt_reg_done': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
        },
    }

    def _default_registration_fee(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id.default_registration_fee_id:
            return user.company_id.default_registration_fee_id.id
        return False

    _columns = {
        'name': fields.char('Name', size=64, select=True, readonly=True),
        'roster_id': fields.many2one('school.roster', 'Academic Year', required=True),
        'student_id': fields.many2one('school.student', 'Student', required=True),
        'registration_fee_id': fields.many2one('product.product', 'Registration Fee', required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'date': fields.date('Date', required=True),
        'state': fields.selection([
            ('draft', 'New'),
            ('cancelled', 'Cancelled'),
            ('pending', 'Pending'),
            ('done', 'Done'),
            ],
            'Status', readonly=True, track_visibility='onchange'),
    }

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'hr.employee', context=c),
        'registration_fee_id': _default_registration_fee,
        'date': fields.date.context_today,
        'state': 'draft',
        'user_id': lambda cr, uid, id, c={}: id,
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'school.roster.enrolment') or '/'
        return super(school_roster_enrolment, self).create(cr, uid, vals, context=context)

school_roster_enrolment()
