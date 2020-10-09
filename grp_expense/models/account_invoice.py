from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    state = fields.Selection(selection_add=[('validated', 'Validated')])
    partner_vat = fields.Char('VAT', related='partner_id.vat')
    invoice_line_number = fields.Integer('Number of Lines', compute='_compute_invoice_line_number')
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
    beneficiario = fields.Many2one(
        "hr.employee", string="Beneficiario", track_visibility="onchange",compute="_compute_carga_datos",
        store=True,
    )
    
    @api.multi
    def _compute_invoice_line_number(self):
        for record in self:
            record.invoice_line_number = len(record.invoice_line_ids)
            
    @api.depends("solicitante_id","ejercicio_id")
    def _compute_carga_datos(self):
        for record in self:
            empleado = record.env["hr.employee"].search(
                [("user_id", "=", record.solicitante_id.id),]
            )
            record.beneficiario=empleado.id
            record.depedence_ueg_id = record.beneficiario.department_id.id            

    @api.multi
    def action_invoice_validate(self):
        if self.mapped('invoice_line_ids').filtered(lambda l: l.importe_presupuesto_disponible <= 0.0):
            raise ValidationError("No se cuenta con presupuesto disponible")
                
        if self.mapped('invoice_line_ids').filtered(
                lambda l: not l.product_id or not l.partidas_id or not l.estructura_id):
            raise UserError(_('The product, partida and structure are required in all the lines'))
        self.l10n_mx_edi_update_sat_status()
        if self.filtered(lambda i: i.l10n_mx_edi_sat_status != 'valid'):
            raise UserError(_('To validate an invoice, this must be valid in the SAT'))
        self.write({'state': 'validated'})

    @api.multi
    def action_get_lines_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('grp_expense', 'action_invoice_line')
        res['domain'] = [('invoice_id', 'in', self.ids)]
        res['context'] = {'default_invoice_id': self.id}
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('price_subtotal', 'invoice_line_tax_ids')
    def _compute_price_grp(self):
        for record in self:
            currency = record.invoice_id and record.invoice_id.currency_id or None
            price = record.price_unit * (1 - (record.discount or 0.0) / 100.0)
            taxes = []
            if record.invoice_line_tax_ids:
                taxes = record.invoice_line_tax_ids.compute_all(
                    price, currency, record.quantity, product=record.product_id, partner=record.invoice_id.partner_id)
            record.amount_tax = sum([tax.get('amount') for tax in taxes.get('taxes')]) if taxes else 0
            record.price_total = record.price_subtotal + record.amount_tax

    amount_tax = fields.Monetary(string='Amount Tax', store=True, readonly=True, compute='_compute_price_grp')
    price_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_price_grp')
    justification_expense = fields.Char(
        'Justification Expense')
    
    @api.multi
    @api.depends("partidas_id", "estructura_id")
    def _compute_importe_presupuesto_disponible(self):        
        for record in self:
            disponible = 0.0
            if record.estructura_id:
                disponible = (
                    record.estructura_id._presupuesto_disponible_anual()
                )
            record.importe_presupuesto_disponible = disponible            

    importe_presupuesto_disponible = fields.Float(
        string="Presupuesto disponible",
        digits=0,
        track_visibility="onchange",
        store=True,
        compute="_compute_importe_presupuesto_disponible",
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        if not self.invoice_id or self.invoice_id.type not in ['in_refund', 'in_invoice'] or not self.product_id:
            return res
        self.name = self._origin.name or self.name
        return res

    @api.onchange('product_id', 'departamento_id')
    def product_id_change(self):
        res = super(AccountInvoiceLine, self).product_id_change()
        if not self.partidas_id:
            self.partidas_id = self.product_id.product_tmpl_id.partida_id.partidas_id
        return res

    @api.multi
    def unlink(self):
        for line in self.filtered(lambda line: line.invoice_id and line.invoice_id.type in ['in_refund', 'in_invoice']):  # noqa
            raise UserError(_('You cannot delete an invoice line'))
        return super(AccountInvoiceLine, self).unlink()
