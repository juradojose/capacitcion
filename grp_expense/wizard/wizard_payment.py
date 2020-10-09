# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class WizardStatesPayment(models.Model):
    _name = "wizard.states.payment"

    @api.model
    def _default_payment(self):
        return self._context.get("active_id")
    
    def _default_state_from(self):
        state_from = self._context.get('state_from',False)
        return state_from
    
    def _default_state_to(self):
        state_to = self._context.get('state_to',False)
        return state_to

    user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, string="Usuario"
    )
    asignado = fields.Many2one(
        "res.users", string="Asignado",
    )
    binnacle_id = fields.Many2one("binnacle.state.payment", string="Bitacora")
    note = fields.Text("Observaciones")
    return_id = fields.Many2one(
        "grp.expense.returns.concept", string="Tipo de Devolución",
    )
    payment_id = fields.Many2one(
        "expense.payment", string="Tramite", default=_default_payment
    )
    
    state_to = fields.Selection(
        [
            ("draft", "Borrador"),
            ("to_authorize", "Por Autorizar"),
            ("first_authorization", "Primera autorización"),
            ("second_authorization", "Segunda autorización"),
            ("received", "Recibida"),
            ("in_review", "En revisión"),
            ("in_review2", "En revisión"),
            ("revised", "Revisada"),
            ("validated", "Validada"),
            ("authorized", "Autorizada"),
            ("shipping_box", "Envío a Caja"),
            ("rejected", "Cancelada"),
            ("observed", "Observada"),
            ("entregado_caja", "Recibido"),
            ("scheduled", "Programado"),
            ("frozen", "Congelado"),
            ("printed", "Impreso"),
            ("sent", "Enviado"),
            ("paid", "Pagado"),
            ("env_sop", "Enviado a Soporte del Gasto"),
            ("env_cont", "Enviado a Contabilidad"),
        ],
        copy=False, default=_default_state_to
    )
    state_from = fields.Selection(
        [
            ("draft", "Borrador"),
            ("to_authorize", "Por Autorizar"),
            ("first_authorization", "Primera autorización"),
            ("second_authorization", "Segunda autorización"),
            ("received", "Recibida"),
            ("in_review", "En revisión"),
            ("in_review2", "En revisión"),
            ("revised", "Revisada"),
            ("validated", "Validada"),
            ("authorized", "Autorizada"),
            ("shipping_box", "Envío a Caja"),
            ("rejected", "Cancelada"),
            ("observed", "Observada"),
            ("entregado_caja", "Recibido"),
            ("scheduled", "Programado"),
            ("frozen", "Congelado"),
            ("printed", "Impreso"),
            ("sent", "Enviado"),
            ("paid", "Pagado"),
            ("env_sop", "Enviado a Soporte del Gasto"),
            ("env_cont", "Enviado a Contabilidad"),
        ],
        copy=False, default=_default_state_from
    )

    @api.multi
    def action_save_data(self):
        
        binnacle_id = self.env["binnacle.state.payment"].create(
            {
                "state_to": self.state_to,
                "expense_id": self.payment_id.id,
                "user_id":self.user_id.id,
                "observations":self.note,
                "asignado":self.asignado,
                "return_id":self.return_id.id
            }
        )
        self.payment_id.write({'state': self.state_to})
        return True
