# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError,ValidationError
from odoo.tools.translate import _

  	

class cls_wizardexpensepagos(models.TransientModel):
    _name = "expense.pagos"

    def _default_solicitud_pago(self):
        sp_obj = self.env['expense.payment']
        solicitudes = sp_obj.browse(self._context.get('active_ids', False))
        
        return solicitudes    

    nombre_cuenta = fields.Many2one('res.partner.bank',string='Nombre de la Cuenta', required=True)
    banco = fields.Char('Banco', related="nombre_cuenta.bank_id.name", readonly=True)
    cuenta = fields.Char('Cuenta', related="nombre_cuenta.acc_number", readonly=True)
    tipo_pago = fields.Selection([
        ('Pago Electronico', 'Pago Electrónico'),
        ('Cheque', 'Pago Cheque'),
        ('Servicio Referenciado', 'Pago Servicio Referenciado'),
        ('Cadenas Productivas', 'Pago Cadenas Productivas')
    ])
    solicitud_pago_ids = fields.Many2many('expense.payment', default=_default_solicitud_pago)
    total = fields.Float(string="Total", compute="_compute_total", readonly=True,)
    
    @api.onchange('tipo_pago')
    def _default_pago_cheque(self):
        for i in self.solicitud_pago_ids:
            if i.account_payment_id.name == 'Cheque nominativo':
                self.tipo_pago = "Cheque"
                
    @api.onchange('solicitud_pago_ids')
    def _default_transfer(self):
        for i in self.solicitud_pago_ids:
            if i.account_payment_id.name == 'Transferencia electrónica de fondos'.decode('utf-8'):
                self.tipo_pago = "Pago Electronico"
    
    @api.multi
    def _compute_total(self):
        self.total = sum([line.total for line in self.solicitud_pago_ids])
    
    @api.multi
    def create_pago_masivo(self):
        for i in self.solicitud_pago_ids:
            if i.state == 'scheduled':
                solicitud = []
                solicitud = self.env["expense.payment"].search([("id","=",i.id)])
                values = {}
                values = {
                    "bank_id": self.nombre_cuenta.bank_id.id,
                    "bank_account": self.nombre_cuenta.acc_number,
                    "forma_pago": self.tipo_pago,
                    "solicitud_pago_ids": [(4,solicitud.id,0)],
                }
                self.env["expense.pagos.masivos"].create(values)
                i.state = "sent"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Para crear un pago la solicitud debe estar en estado programado")
        return self.action_open_wizard(binnacle_id)
    
    @api.multi
    def create_cheque(self):
        for i in self.solicitud_pago_ids:
            if i.state == 'scheduled' and i.account_payment_id.name == 'Cheque nominativo' and i.avoid_duplicate_check == False:
                solicitud = []
                solicitud = self.env["expense.payment"].search([("id","=",i.id)])
                values = {}
                values = {
                    "solicitud_pago_ids": [(4,solicitud.id,0)],
                    "cuenta": self.nombre_cuenta.id,
                }
                self.env["expense.impresion.cheques"].create(values)
                i.state = "create_check"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Para crear un cheque la forma de pago debe ser Cheque nominativo / \n La solicitud debe estar en estado programado / \n El cheque ya se elaboró para una solicitud seleccionada")
        return self.action_open_wizard(binnacle_id)

    @api.multi
    def create_pago_referenciado(self):
        for i in self.solicitud_pago_ids:
            if i.state == 'scheduled':
                solicitud = []
                solicitud = self.env["expense.payment"].search([("id","=",i.id)])
                values = {}
                values = {
                    "bank_id":self.nombre_cuenta.bank_id.id,
                    "bank_account": self.nombre_cuenta.acc_number,
                    "forma_pago":self.tipo_pago,
                    "solicitud_pago_ids": [(4,solicitud.id,0)],
                }
                self.env["expense.pagos.masivos"].create(values)
                i.state = "sent"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Para crear un pago referenciado la solicitud debe estar en estado programado")
        return self.action_open_wizard(binnacle_id)
    
    @api.multi
    def action_open_wizard(self, binnacle):
        data_wizar = {
            "binnacle_id": binnacle.id,
        }
        wizard_id = self.env["wizard.states.payment.masivo"].create(data_wizar)
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.states.payment.masivo",
            "view_mode": "form",
            "view_type": "form",
            "view_id": False,
            "target": "new",
            "res_id": wizard_id.id,
        }
            
class cls_wizardrecepcionpagos(models.TransientModel):
    _name = "expense.pagos.recepcion"
    
    def _default_solicitud_pago(self):
        sp_obj = self.env['expense.payment']
        solicitudes = sp_obj.browse(self._context.get('active_ids', False))
        
        return solicitudes
    
    solicitud_pago_ids = fields.Many2many('expense.payment', default=_default_solicitud_pago)
    total = fields.Float(string="Total", compute="_compute_total", readonly=True,)
    
    @api.multi
    def _compute_total(self):
        self.total = sum([line.total for line in self.solicitud_pago_ids])
        
    @api.multi
    def action_masivo(self):
        for i in self.solicitud_pago_ids:
            if i.state == "shipping_box":
                i.state = "entregado_caja"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Solamente se pueden recibir solicitudes en estado de envío a caja")
        return self.action_open_wizard(binnacle_id)
    
    @api.multi
    def action_open_wizard(self, binnacle):
        data_wizar = {
            "binnacle_id": binnacle.id,
        }
        wizard_id = self.env["wizard.states.payment.masivo"].create(data_wizar)
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.states.payment.masivo",
            "view_mode": "form",
            "view_type": "form",
            "view_id": False,
            "target": "new",
            "res_id": wizard_id.id,
        }
            
    @api.multi
    def masivo_congelar(self):
        for i in self.solicitud_pago_ids:
            if i.state == "entregado_caja":
                i.state = "frozen"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Solamente se pueden congelar solicitudes en estado de recibido")
        return self.action_open_wizard(binnacle_id)
    
    @api.multi
    def action_programar_solicitudes(self):
        for i in self.solicitud_pago_ids:
            if i.state == "entregado_caja":
                i.state = "scheduled"
                binnacle_id = i.env["binnacle.state.payment"].create(
                    {
                        "state_to": i.state,
                        "expense_id": i.id,
                    }
                )
            else:
                raise ValidationError("Solamente se pueden programar solicitudes en estado de recibido")
        return self.action_open_wizard(binnacle_id)
                
