# -*- coding: utf-8 -*-

import datetime
from odoo import fields, models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def compute_subrange_days_by_year(self, date):
        seq_date_range = []
        year = fields.Date.from_string(date).strftime('%Y')
        date_from = datetime.datetime.strptime('{}-01-01'.format(year), '%Y-%m-%d')
        date_to = datetime.datetime.strptime('{}-12-31'.format(year), '%Y-%m-%d')
        date_generated = [date_from + datetime.timedelta(days=x) for x in range(0, (date_to - date_from).days)]
        for day in date_generated:
            date_range = self.env['ir.sequence.date_range'].search([
                ('sequence_id', '=', self.id),
                ('date_from', '>=', day),
                ('date_to', '<=', day)
            ], order='date_from desc')
            if not date_range:
                seq_date_range = self.env['ir.sequence.date_range'].sudo().create({
                    'date_from': day,
                    'date_to': day,
                    'sequence_id': self.id,
                })
        return seq_date_range if seq_date_range else False
