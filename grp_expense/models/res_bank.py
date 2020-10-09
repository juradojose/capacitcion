# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerBank(models.Model):
    _name = "res.partner.bank"
    _inherit = ['res.partner.bank', 'mail.thread']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated')], default='draft', track_visibility='onchange',
        help='If the values are correct, could be validated to could be used on expenses.')

    def action_validate(self):
        """Indicate that the bank account is correct"""
        self.write({'state': 'validated'})
