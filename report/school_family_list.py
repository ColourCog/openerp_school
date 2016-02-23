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

report_sxw.report_sxw(
    'report.school.family',
    'school.report',
    'addons/school/report/school_family_list.rml',
    parser=school_report_family,
    header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
