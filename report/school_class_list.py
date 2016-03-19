# -*- coding: utf-8 -*-

import time
from openerp.report import report_sxw
from school.tools import age, count, get_current_academic_period

class school_report_class(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(school_report_class, self).__init__(
                cr,
                uid,
                name,
                context=context)
        self.localcontext.update({
            'age': age,
            'count': count,
            'year': get_current_academic_period(self.cr, self.uid, context=context)
        })

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if data.get('model') and data['model'] == 'ir.ui.menu':
            new_ids = self.pool.get('school.class').search(self.cr, self.uid, [('state','=','open')])
            objects = self.pool.get('school.class').browse(self.cr, self.uid, new_ids)
        return super(school_report_class, self).set_context(objects, data, new_ids, report_type=report_type)


report_sxw.report_sxw(
    'report.school.class.print.surname',
    'school.class',
    'addons/school/report/school_family_list.rml',
    parser=school_report_class,
    header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
