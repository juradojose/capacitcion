# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import  ValidationError
import random
import string 


class Course(models.Model):
    _name = 'openacademy.course'
    _description = "OpenAcademy Courses"

    name = fields.Char(string='Nombre')
    description=fields.Text(String='Descripción')
    fecha=fields.Date(string="Fecha")
    decimal=fields.Float(string="Número decimal")
    entero=fields.Integer(string="Entero")
    bina=fields.Binary(string="Foto")
    seleccion=fields.Selection([('a', 'A'), ('b', 'B')])
    boolean=fields.Boolean(string="Boolean")
    char=fields.Char(string="char")
    boolean1=fields.Boolean(string="Promediar?")
    pr1=fields.Float(string="Unidad 1")
    pr2=fields.Float(string="Unidad 2")
    pr3=fields.Float(string="Unidad 3")
    pr=fields.Float(defalut='promediar')

    name2 = fields.Char(required=True,default='Click on generate name!')
    password = fields.Char()

    @api.constrains('boolean')
    def afun(self):
        if self.boolean==False:
            raise ValidationError(
                        "Entro a la validacion"
                    )

    @api.one
    def generate_promedio(self):
            self.write({'pr':((self.pr1 + self.pr2 + self.pr3)/3)})

    @api.one
    def generate_record_name(self):
        #Generates a random name between 9 and 15 characters long and writes it to the record.
        self.write({'name2': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(9,15)))})
    
    @api.one
    def generate_record_password(self):
        #Generates a random password between 12 and 15 characters long and writes it to the record.
        self.write({'password': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(random.randint(12,15)))})

    @api.one
    def clear_record_data(self):
        self.write({
            'name2': '',
	        'password': '',
        })

class Alumnos(models.Model):
    _name = 'openacademy.course2'
    _description = "OpenAcademy Alumnos"

    foto=fields.Binary(string="Foto")
    name3 = fields.Char(string="Nombre")
    description3=fields.Text(string='Descripción')
    fecha3 =fields.Date(string="Fecha")
    many = fields.Many2one(comodel_name='openacademy.course3', string='Carrera')
    barra = fields.Selection([
            ('concept', 'Concept'),
            ('started', 'Started'),
            ('progress', 'In progress'),
            ('finished', 'Done'),
            ],default='concept')
    
    @api.one
    def concept_progressbar(self):
        self.write({
            'barra': 'concept',
        })
 
    #This function is triggered when the user clicks on the button 'Set to started'
    @api.one
    def started_progressbar(self):
        self.write({
        'barra': 'started'
        })
 
    #This function is triggered when the user clicks on the button 'In progress'
    @api.one
    def progress_progressbar(self):
        self.write({
        'barra': 'progress'
        })
 
    #This function is triggered when the user clicks on the button 'Done'
    @api.one
    def done_progressbar(self):
        self.write({
        'barra': 'finished',
        })
    
    
    

class Carrera(models.Model):
    _name = 'openacademy.course3'
    _description = "OpenAcademy Carrera"
    _rec_name="seleccion2"

    seleccion2=fields.Selection(string='Carrera', selection=[('sf', 'Software'), ('c', 'Civil'), ('I', 'IRT')])
    semestre=fields.Selection(string='Semestre', selection=[('1', 'Primero'), ('2', 'Segundo'), ('3', 'Tercero'), ('4', 'Cuarto')])
    grupo=fields.Selection(string='Grupo', selection=[('a', 'A'), ('b', 'B'), ('c', 'C')])
    one = fields.One2many('openacademy.course2', 'many')