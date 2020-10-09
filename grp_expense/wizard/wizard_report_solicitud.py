# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError,ValidationError
from odoo.tools.translate import _

class cls_wizardReportSolicitud(models.TransientModel):
    _name = 'expense.reportes.solicitud'
    
    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id
    
    def _default_solicitud_pago(self):
        sp_obj = self.env['expense.payment']
        solicitudes = sp_obj.browse(self._context.get('active_ids', False))
        
        return solicitudes
    
    solicitud_pago_ids = fields.Many2many('expense.payment', default=_default_solicitud_pago)
    company_id = fields.Many2one('res.company', string='Company', required=True,default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency',
        default=_default_currency, 
        string="Currency",
        required=True,
        readonly=True,
        track_visibility="always")
    puesto_partner = fields.Many2one(
        "hr.job", string="Puesto", related="partner_id.job_id"
    )
    partner_id = fields.Many2one(
        "hr.employee", string="Beneficiario", track_visibility="onchange"
    )
    
    def print_report(self):
        for x in self.solicitud_pago_ids:
            if x.state != 'entregado_caja':
                raise ValidationError("Solamente solicitudes en estado de Recibido en caja")
        return self.env["report"].get_action(self, "grp_expense.report_sol_envio_caja")