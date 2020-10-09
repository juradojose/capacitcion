import time
import locale
from datetime import datetime, timedelta
from odoo import fields, api, models
from dateutil.parser import parse
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class cls_report_carta_aceptacion(models.AbstractModel):
    _name = 'report.grp_expense.report_carta_aceptacion'
    
    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env['expense.payment'].browse(docids)
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
        date = fields.Datetime.context_timestamp(
            self.with_context(tz='America/Mexico_City'),  datetime.strptime(str(docs.date), '%Y-%m-%d')+timedelta(days=1)).strftime('%d de %B de %Y')

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'date_today': date,
        }
        return self.env['report'].render('grp_expense.report_carta_aceptacion', docargs)

class cls_report_recibo(models.AbstractModel):
    _name = 'report.grp_expense.report_recibo'

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env['expense.payment'].browse(docids)
        locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")
        date = fields.Datetime.context_timestamp(
            self.with_context(tz='America/Mexico_City'), datetime.now()).strftime('%d de %B de %Y')

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,          
            'date_today': date,
        }
        return self.env['report'].render('grp_expense.report_recibo', docargs)
