# -*- coding: utf-8 -*-

import time
from datetime import datetime, date
from openerp.report import report_sxw


class school_report_class(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(school_report_class, self).__init__(
                cr,
                uid,
                name,
                context=context)
        self.localcontext.update({
            'age': self._age,
            'count': self._count,
        })

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if data.get('model') and data['model'] == 'ir.ui.menu':
            new_ids = self.pool.get('school.class').search(self.cr, self.uid, [('state','=','open')])
            objects = self.pool.get('school.class').browse(self.cr, self.uid, new_ids)
        return super(school_report_class, self).set_context(objects, data, new_ids, report_type=report_type)

    def _age(self, when, on=None):
        fmt = '%Y-%m-%d'
        when = datetime.strptime(when, fmt)
        if on is None:
            on = date.today()
        earl = (on.month, on.day) < (when.month, when.day)
        year = on.year - when.year - (earl)
        month = earl and (11 - when.month + on.month) or (on.month - when.month)
        return "{0}yrs. {1}m.".format(year, month)

    def _count(self, items, children=None):
        if children:
            sums = 0
            for item in items:
                try:
                    sums += len(getattr(item, children, 0))
                except AttributeError:
                    pass
            return sums
        return len(items)

report_sxw.report_sxw(
    'report.school.class.print.surname',
    'school.class',
    'addons/school/report/school_family_list.rml',
    parser=school_report_class,
    header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
