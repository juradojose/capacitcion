# -*- coding: utf-8 -*-

from odoo import models, fields

class GrpExpenseBase(models.Model):
    _name = 'grp.expense.base'

    key = fields.Char()
    name = fields.Char(required=True)

class ZipCode(models.Model):
    _inherit = 'grp.expense.base'
    _name = 'grp.expense.zip.code.catalog'

class Town(models.Model):
    _inherit = 'grp.expense.base'
    _name = 'grp.expense.town.catalog'

class Suburb(models.Model):
    _inherit = 'grp.expense.base'
    _name = 'grp.expense.suburb.catalog'

class BeneficiaryType(models.Model):
    _inherit = 'grp.expense.base'
    _name = 'grp.expense.beneficiary.type.catalog'

