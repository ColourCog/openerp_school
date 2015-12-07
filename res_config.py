from openerp.tools.translate import _
from openerp.osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"

    _columns = {
        'default_registration_fee_id': fields.many2one(
            'product.product',
            'Registration Fee'),
    }

res_company()

class school_config_settings(osv.osv_memory):
    _name = 'school.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),

        'default_registration_fee_id': fields.related(
            'company_id',
            'default_registration_fee_id',
            type='many2one',
            relation='product.product',
            string="Registration Fee"),
    }

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    _defaults = {
        'company_id': _default_company,
    }

    def create(self, cr, uid, values, context=None):
        id = super(school_config_settings, self).create(cr, uid, values, context)
        # Hack: to avoid some nasty bug, related fields are not written upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, fields.related) and fname in values:
                vals[fname] = values[fname]
        self.write(cr, uid, [id], vals, context)
        return id

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        # update related fields
        values = {
            'default_registration_fee_id': False,
        }
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            values.update({
                'default_registration_fee_id': company.default_registration_fee_id and company.default_registration_fee_id.id or False,
            })
        return {'value': values}
