#/bin/env python2

import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler
_logger = logging.getLogger(__name__)

class school_roster(osv.osv):
    _name = 'school.roster'
    _description = 'Grade Roster'

    def _get_roster_from_enrolment(self, cr, uid, ids, context=None):
        enrol_obj = self.pool.get('school.roster.enrolment')
        return [e.roster_id.id
                for e in enrol_obj.browse(cr, uid, ids, context=context)]

    def _get_free_seats(self, cr, uid, ids, name, args, context):
        if not ids:
            return {}
        res = {}
        for roster in self.browse(cr, uid, ids, context=context):
            res[roster.id] = roster.seats_max - len([e for e in roster.enrolment_ids])
        return res

    _columns = {
        'name': fields.char('Name', size=64, select=True, readonly=True),
        'year_id': fields.many2one('school.academic.year', 'Academic Year', required=True),
        'grade_id': fields.many2one('school.academic.grade', 'Grade', required=True),
        'enrolment_ids': fields.one2many(
            'school.roster.enrolment',
            'roster_id',
            'Enrolments'),
        'seats_max': fields.integer('Maximum seats', required=True),
        'seats_free': fields.function(
            _get_free_seats,
            type='integer',
            string='Available seats',
            store={
                _name: (lambda self, cr, uid, ids, c: ids, ['enrolment_ids', 'seats_max'], 10),
                'school.roster.enrolment': (_get_roster_from_enrolment, None, 10),
            }),
    }

    def create(self, cr, uid, vals, context=None):
        grade = self.pool.get('school.academic.grade').browse(cr, uid, [vals['grade_id']])[0]
        year = self.pool.get('school.academic.year').browse(cr, uid, [vals['year_id']])[0]
        if vals.get('name', '/') == '/':
            vals['name'] = ' '.join([grade.name, year.name])
        return super(school_roster, self).create(cr, uid, vals, context=context)

school_roster()
