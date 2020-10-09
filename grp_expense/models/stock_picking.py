# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id

    number_before = fields.Char(string="No. de Recibo Anterior")
    number_receipt_before = fields.Char(string="No. de Contrarecibo")
    date_before = fields.Date(string="Fecha de Contrarecibo")
    type_receipt = fields.Selection(
        [("service", "Servicio"), ("product", "Material")],
        string="Tipo de Recepción",
        track_visibility="onchange",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        readonly=True,
        default=_default_currency,
        track_visibility="always",
    )
    user_id = fields.Many2one(
        "res.users", string="Solicitado por", default=lambda self: self.env.user
    )
    date_order = fields.Date(string="Fecha OC", related="purchase_id.fechapedidocompra",)
    dependence_id = fields.Many2one(
        "hr.department",
        string="Dependencia",
        store=True,
        related="purchase_id.dependencia",
    )
    department_id = fields.Many2one(
        "hr.department", string="Departamento (UEG)", related="purchase_id.department_id",
    )
    unit_responsable = fields.Char(
        string="Unidad Responsable (UR)", related="purchase_id.unidad_responsable",
    )
    origin_source = fields.Many2one(
        "recaudador.fuentesfinanciamiento",
        string="Origen (de los recursos)",
        readonly=True,
        related="purchase_id.origen",
    )
    budget_justification = fields.Many2one(
        "justification.catalog",
        string="Justificación presupuestal",
        readonly=True,
        related="purchase_id.justificacion_presupuestal",
    )
    event_general = fields.Many2one(
        "model.cont.eventos",
        string="Evento General",
        readonly=True,
        related="purchase_id.evento_general",
    )
    specific_cluster = fields.Many2one(
        "grp_account.accounting.grouper",
        string="Agrupador Especifico",
        readonly=True,
        related="purchase_id.agrupador_especifico",
    )
    general_grouter = fields.Many2one(
        "grp_account.accounting.grouper",
        string="Agrupador Genérico",
        readonly=True,
        related="purchase_id.agrupador_general",
    )
    digital_invoice = fields.Many2one("account.invoice", string="Factura",)
    date_invoice = fields.Date(
        string="Fecha de Factura", related="digital_invoice.date_invoice", readonly=True,
    )
    total_invoice = fields.Monetary(
        string="Total de Factura",
        related="digital_invoice.amount_total",
        readonly=True,
        currency_field="currency_id",
    )
    bias = fields.Boolean(string="Parcialidad", related="purchase_id.parcialidades")
    number_bias = fields.Char(string="No. de Parcialidad de OC",)
    balance_oc = fields.Float(
        string="Saldo de OC", compute="_compute_balance", readonly=True
    )
    requisition_id = fields.Many2one(
        "purchase.requisition",
        string="Requisición",
        readonly=True,
        related="purchase_id.requisition_id",
    )

    date_requisition = fields.Date(
        string="Fecha de Requisición",
        readonly=True,
        related="purchase_id.requisition_id.fecha_emision",
    )
    number_check = fields.Char(string="No. de Cheque")
    date_check = fields.Date(string="Fecha de Cheque")
    retention = fields.Float(string="% Retencion",)
    type_receipt_migration = fields.Char(string="Tipo de Recibo",)
    atn_supplier = fields.Selection(
        [
            ("excellent", "Excelente"),
            ("ok", "Bueno"),
            ("regular", "Regular"),
            ("bad", "Malo"),
        ],
        string="At’n del proveedor",
    )
    obs_atn = fields.Char(string="Obs. Atención",)
    binnacle_ids = fields.One2many(
        "binnacle.state.picking", "picking_id", string="Bitácora",
    )

    @api.multi
    def do_new_transfer(self):
        res = super(StockPicking, self).do_new_transfer()
        if not self.digital_invoice:
            raise UserError("No ha seleccionado la factura")
        if not self.total_invoice == sum([line.price_total for line in self.move_lines]):
            raise UserError("El total de la Factura no es igual al total del recibo")
        if (
            not self.bias
            and sum([line.price_total for line in self.move_lines])
            != self.purchase_id.amount_total
        ):
            raise UserError("Usted no puede generar parcialidades")
        return res

    @api.multi
    def _compute_balance(self):
        for x in self:
            x.balance_oc = (
                sum([line.price_subtotal for line in x.purchase_id.order_line])
                - x.total_invoice
            )

    @api.multi
    def action_print_picking_grp(self):
        return self.env["report"].get_action(self, "grp_expense.report_stock_picking")


class BinnacleStatePicking(models.Model):
    _name = "binnacle.state.picking"

    user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user, readonly=True
    )
    date = fields.Datetime(
        string="Fecha", readonly=True, default=lambda self: fields.datetime.now()
    )
    observations = fields.Text(string="Observaciones")
    state = fields.Char(string="Estado", readonly=True)
    picking_id = fields.Many2one(
        "stock.picking", string="Movimiento", ondelete="restrict", readonly=True,
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.multi
    def name_get(self):
        res = []
        for obj in self:
            res.append([obj.id, "%s" % (obj.pedidocompra)])
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends("product_uom_qty", "price_unit", "taxes_id")
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(
                line.price_unit,
                line.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.picking_id.partner_id,
            )
            prod = line.product_uom_qty * line.price_unit
            line.update(
                {
                    "price_tax": taxes["total_included"] - taxes["total_excluded"],
                    "price_total": taxes["total_included"],
                    "price_subtotal": taxes["total_included"],
                    "subtotal_without_tax": prod,
                    "qty_pending": line.qty_po - line.qty_received,
                }
            )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        readonly=True,
        related="company_id.currency_id",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Departamento",
        readonly=True,
        related="purchase_line_id.department_id",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        readonly=True,
        related="purchase_line_id.empleado_id",
    )

    key_id = fields.Many2one(
        "purchase.estructura.contable",
        string="Clave presupuestal",
        readonly=True,
        related="purchase_line_id.estructura_contable_ids",
    )

    qty_invoiced = fields.Float(
        string="Cant. Facturada", readonly=True, related="purchase_line_id.qty_invoiced",
    )
    qty_po = fields.Float(
        string="Cant. PO", readonly=True, related="purchase_line_id.product_qty",
    )
    qty_received = fields.Float(
        string="Cant. recibida", readonly=True, related="purchase_line_id.qty_received",
    )
    qty_pending = fields.Float(
        string="Cant. Pendiente", readonly=True, compute="_compute_amount",
    )
    price_unit = fields.Float(
        string="Precio unitario", readonly=True, related="purchase_line_id.price_unit",
    )
    price_subtotal = fields.Monetary(
        compute="_compute_amount", string="Subtotal", currency_field="currency_id",
    )
    price_total = fields.Monetary(
        compute="_compute_amount", string="Total", currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        compute="_compute_amount",
        string="Importe Impuestos",
        currency_field="currency_id",
    )
    description = fields.Text(related="purchase_line_id.name", string="Descripción",)
    subtotal_without_tax = fields.Float(string="Subtotal", compute="_compute_amount",)
    taxes_id = fields.Many2many(
        "account.tax",
        string="Impuestos",
        domain=["|", ("active", "=", False), ("active", "=", True)],
        related="purchase_line_id.taxes_id",
    )
