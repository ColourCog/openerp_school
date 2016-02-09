#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  res_partner.py
#


from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        "children_ids": fields.one2many("school.student", "billing_partner_id", "Children"),
    }

res_partner()

