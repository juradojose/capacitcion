# -*- coding: utf-8 -*-

from odoo import models, fields


class GrpExpenseReturnsConcept(models.Model):
    _name = "grp.expense.returns.concept"

    name = fields.Char(string="Description")
