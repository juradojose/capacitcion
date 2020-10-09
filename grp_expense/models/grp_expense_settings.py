# -*- coding: utf-8 -*-

from odoo import fields, models


class ExpenseConfigSettings(models.TransientModel):
    _name = "grp.expense.config.settings"
    _inherit = "res.config.settings"

    company_id = fields.Many2one(
        "res.company",
        "Company",
        default=lambda self: self.env.user.company_id,
        required=True,
    )
    allow_create_expense_suppliers = fields.Boolean(
        string="Permitir crear beneficiarios",
        related="company_id.allow_create_expense_suppliers",
        help="If this field is False, not allow create suppliers from import process.",
    )
    solicitud_report_header = fields.Binary(
        related='company_id.solicitud_report_header',string="Encabezado Reporte de Solicitud de Pago",help="Este campo almacena la imagen a utilizar como encabezado del reporte de solicitud de pago."
    )
    recibo_report_header = fields.Binary(
        related='company_id.recibo_report_header',string="Encabezado Reporte de Recibo",help="Este campo almacena la imagen a utilizar como encabezado del reporte de recibo."
    )
    carta_report_header = fields.Binary(
        related='company_id.carta_report_header',string="Encabezado Reporte de Carta de Aceptación",help="Este campo almacena la imagen a utilizar como encabezado del reporte de carta de aceptación."
    )
    devoluciones_report_header = fields.Binary(
        related='company_id.devoluciones_report_header',string="Encabezado Reporte de Devoluciones",help="Este campo almacena la imagen a utilizar como encabezado del reporte de devoluciones."
    )
    relacion_fact_report_header = fields.Binary(
        related='company_id.relacion_fact_report_header',string="Encabezado Reporte de Relación de Facturas",help="Este campo almacena la imagen a utilizar como encabezado del reporte de relación de facturas."
    )
    contrarecibo_report_header = fields.Binary(
        related='company_id.contrarecibo_report_header',string="Encabezado Reporte de Contrarecibo",help="Este campo almacena la imagen a utilizar como encabezado del reporte de contrarecibo."
    )
    solicitud_envio_caja_header = fields.Binary(
        related='company_id.solicitud_envio_caja_header',string="Encabezado Reporte de Solicitudes en estado de Envío a Caja",help="Este campo almacena la imagen a utilizar como encabezado del reporte de Solicitudes de Pago en estado de envío a caja."
    )


class PurchaseConfigSettings(models.TransientModel):
    _inherit = "purchase.config.settings"

    picking_report_header = fields.Binary(
        related="company_id.picking_report_header",
        string="Encabezado Recepción de Materiales y Servicios.",
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de Recepción de Materiales y Servicios.",
    )
