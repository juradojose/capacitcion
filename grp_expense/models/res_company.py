# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    allow_create_expense_suppliers = fields.Boolean(string="Permitir crear beneficiarios")
    picking_report_header = fields.Binary(
        help=u"Este campo almacena la imagen a utilizar como encabezado del reporte de Recepción de Materiales y Servicios."
    )
    solicitud_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de solicitud de pago."
    )
    recibo_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de recibo."
    )
    carta_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de carta de aceptación."
    )
    devoluciones_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de devoluciones."
    )
    relacion_fact_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de relación de facturas."
    )
    contrarecibo_report_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de contrarecibo."
    )
    solicitud_envio_caja_header = fields.Binary(
        help="Este campo almacena la imagen a utilizar como encabezado del reporte de Solicitudes de Pago en estado de envío a caja."
    )
