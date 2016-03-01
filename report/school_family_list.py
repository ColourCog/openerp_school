# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.report import report_sxw


class school_report_family(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(school_report_family, self).__init__(
                cr,
                uid,
                name,
                context=context)

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = self.pool.get('school.student').search(self.cr, self.uid, [('state','=','student')])
            objects = self.pool.get('school.student').browse(self.cr, self.uid, new_ids)
        return super(report_account_common, self).set_context(objects, data, new_ids, report_type=report_type)

report_sxw.report_sxw(
    'report.school.student.print.family',
    'school.student',
    'addons/school/report/school_family_list.rml',
    parser=school_report_family,
    header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
