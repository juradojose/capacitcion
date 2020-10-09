# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InvoiceLineUpdateRubro(models.TransientModel):
    _name = 'invoice.line.update.rubro'

    @api.model
    def default_get(self, fields_list):
        res = super(InvoiceLineUpdateRubro, self).default_get(fields_list)
        invoice = self.env['account.invoice.line'].browse(self._context.get('active_id')).invoice_id
        res['ejercicio_id'] = invoice.ejercicio_id.id
        return res

    partida_id = fields.Many2one(
        'rubro.partida', 'Partida', help='Partida to assign on the invoice lines')
    estructura_id = fields.Many2one(
        'purchase.estructura.contable', 'Clave Presupuestal',domain="[('partidas_id','=',partida_id),('departamento_id','=',depedence_ueg_id),('ejercicio_id','=',ejercicio_id)]",
        help='Clave Presupuestal to assign on the invoice lines')
    ejercicio_id = fields.Many2one(
        'account.fiscalyear', 'Ejercicio Fiscal')    
    solicitante_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        default=lambda self: self.env["res.users"].search([("id", "=", self._uid)]),
    )
    depedence_ueg_id = fields.Many2one(
        "hr.department",
        string="Departamento (UEG)",
        compute="_compute_carga_datos",
        store=True,
    )
    partner_id = fields.Many2one(
        "hr.employee", string="Beneficiario", track_visibility="onchange",compute="_compute_carga_datos",
        store=True,
    )

    def assign_partida(self):
        lines = self.env['account.invoice.line'].browse(self._context.get('active_ids'))
        if self.partida_id:
            lines.write({'partidas_id': self.partida_id.id})
        if self.estructura_id:
            lines.write({'estructura_id': self.estructura_id.id})
    
    @api.depends("solicitante_id","ejercicio_id")
    def _compute_carga_datos(self):     
        empleado = self.env["hr.employee"].search(
            [("user_id", "=", self.solicitante_id.id),]
        )
        self.partner_id=empleado.id
        self.depedence_ueg_id = self.partner_id.department_id.id
