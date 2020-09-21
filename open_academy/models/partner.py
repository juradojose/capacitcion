# -*- coding: utf-8 -*-
from odoo import fields, models, api

class Partner(models.Model):
    _inherit = 'res.partner'

    # Add a new column to the res.partner model, by default partners are not
    # instructors
    instructor = fields.Boolean("Instructor", default=False)

    session_ids = fields.Many2many('openacademy.course2',
    string="Attended Sessions", readonly=True)

    contri=fields.Boolean(string="Contribuyente")
    tel=fields.Char(string="Telegram")
    fac=fields.Char(string="Facebook")
    curp=fields.Char(string="Curp")
    sex=fields.Selection(string="Sexo", selection=[('a', 'Mujer'), ('b', 'Hombre'),('c','Otro')])
    tip=fields.Selection(string="Tipo de empresa", selection=[('a', 'Chica'), ('b', 'Mediana'),('c','Grande')])
    
    centro=fields.Text(string='Centro: 6181226104')
    zapata=fields.Text(string='Zapata: 6181236104') 
    fuen=fields.Text(string='Fuentes: 6181246104')

    @api.multi
    def generate_report(self):
        return self.env['report'].get_action(self, 'open_academy.parner_inherit_report_ind')