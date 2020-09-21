# -*- coding: utf-8 -*-
from odoo import fields, models, api

class SecurityModel(models.Model):
    _name = 'academy.sec'
    _description = "Security Model"

    name=fields.Char(string="Nombre", required=True)
    user_id=fields.Many2one("res.users", string="Responsivos")