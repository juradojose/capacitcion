# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions


class WizardStatesPayment(models.Model):
    _name = "wizard.states.payment.masivo"

    @api.model
    def _default_payment(self):
        return self._context.get("active_id")

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
        "purchase.requisition", string="Tramite", default=_default_payment
    )

    @api.multi
    def action_save_data(self):
        self.payment_id.write(
            {"user_id": self.user_id.id,}
        )
        self.binnacle_id.observations = self.note
        return True