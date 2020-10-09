# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseImportXml(models.Model):
    _name = "purchase.import.xml"

    date = fields.Date(string="Fecha")
    serie = fields.Char(string="Serie")
    folio = fields.Integer(string="Folio")
    rfc_emisor = fields.Char(string="RFC Emisor")
    razon_social = fields.Char(string="Razón Social")
    rfc_receptor = fields.Char(string="RFC Receptor")
    importe = fields.Float(string="Importe")
    state = fields.Selection(
        [("valido", "Válido"), ("invalido", "Inválido"),], string="Estado",
    )
    descripcion = fields.Text(string="Descripción")
    sp_relacionada = fields.Char(string=" SP Relacionada")


class PurchaseNoValidateXml(models.Model):
    _name = "purchase.no.validate.xml"

    date = fields.Datetime(string="Fecha/Hora")
    note = fields.Char(string="Observaciones")
    line_no_validate_ids = fields.One2many(
        "purchase.no.validate.xml.line", "no_validate_id", "Detalle"
    )


class PurchaseNoValidateXmlLine(models.Model):
    _name = "purchase.no.validate.xml.line"

    date = fields.Char(string="Fecha")
    number_invoice = fields.Char(string="Número de Factura")
    razon_social = fields.Char(string="Razón Social")
    importe = fields.Float(string="Importe")
    state = fields.Selection(
        [("valido", "Válido"), ("invalido", "Inválido"),], string="Estado",
    )
    descripcion = fields.Text(string="Descripción")
    no_validate_id = fields.Many2one("purchase.no.validate.xml", string="Detalle")


class ResPartnerSP(models.Model):
    _inherit = "res.partner"

    expense_support = fields.Boolean(string="Soporte del Gasto")
