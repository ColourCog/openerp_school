#/bin/env python2

from datetime import datetime, date
import logging
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

GRADING_METHOD = [
    ('numeric', 'Numeric'),
    ('alpha', 'Alphabetic')]

# http://www.educationoasis.com/resources/Articles/beginners_guide_grades.htm
# Rationale: I might need weighting later, so I need to store numerical
# values for aplhabetica grades.

ALPHA_GRADING = [
    ('43', 'A+'),
    ('40', 'A'),
    ('37', 'A-'),
    ('33', 'B+'),
    ('30', 'B'),
    ('27', 'B-'),
    ('23', 'C+'),
    ('20', 'C'),
    ('17', 'C-'),
    ('13', 'D+'),
    ('10', 'D'),
    ('7', 'D-'),
    ('0', 'F')]

ALPHA_DICT= {
    '43': 'A+',
    '40': 'A',
    '37': 'A-',
    '33': 'B+',
    '30': 'B',
    '27': 'B-',
    '23': 'C+',
    '20': 'C',
    '17': 'C-',
    '13': 'D+',
    '10': 'D',
    '7': 'D-',
    '0': 'F'}

def resolve_id_from_context(target, context=None):
    if context is None:
        context = {}
    if type(context.get(target)) in (int, long):
        return context[target]
    return None

def generic_generate_invoice(cr, uid, product_id, partner_id, student_name, transaction_name, context):
    if not context:
        context = {}
    ctx = context.copy()
    ctx.update({'account_period_prefer_normal': True})
    pool_obj = pooler.get_pool(cr.dbname)

    period_obj = pool_obj.get('account.period')
    inv_obj = pool_obj.get('account.invoice')
    inv_line_obj = pool_obj.get('account.invoice.line')
    product_obj = pool_obj.get('product.product')

    product = product_obj.browse(cr, uid, product_id, context)
    uom_id = product.uom_id.id

    line = {
        'name': "%s for %s" % (product.name, student_name),
        'product_id': product_id,
        'quantity': 1,
        }
    # run inv_line_obj's onchange to update
    n = inv_line_obj.product_id_change(
        cr,
        uid,
        False,
        product_id,
        uom_id,
        qty=1,
        name="%s for %s" % (product.name, student_name),
        type='out_invoice',
        partner_id=partner_id,
        company_id=None,
        context=None)['value']
    line.update(n)
    line.update({'name': "%s for %s" % (product.name, student_name)})

    inv_line = (0, 0, line)

    invoice = {
        'type': 'out_invoice',
        'partner_id': partner_id,
        'invoice_line': [inv_line],
        }
    # run inv_obj's onchange to update
    n = inv_obj.onchange_partner_id(
        cr,
        uid,
        False,
        'out_invoice',
        partner_id,
        date_invoice=False,
        payment_term=False,
        partner_bank_id=False,
        company_id=False)['value']
    invoice.update(n)

    inv_id = inv_obj.create(cr, uid, invoice, context=ctx)
    #~ inv_obj.action_date_assign(cr,uid,[inv_id],context)
    #~ inv_obj.action_move_create(cr,uid,[inv_id],context=context)
    #~ inv_obj.action_number(cr,uid,[inv_id],context)
    #~ inv_obj.invoice_validate(cr,uid,[inv_id],context=context)

    return inv_id

def age(when, on=None):
    fmt = '%Y-%m-%d'
    when = datetime.strptime(when, fmt)
    if on is None:
        on = date.today()
    earl = (on.month, on.day) < (when.month, when.day)
    year = on.year - when.year - (earl)
    month = earl and (11 - when.month + on.month) or (on.month - when.month)
    return "{0}yrs. {1}m.".format(year, month)

def count(items, children=None):
    if children:
        sums = 0
        for item in items:
            try:
                sums += len(getattr(item, children, 0))
            except AttributeError:
                pass
        return sums
    return len(items)

