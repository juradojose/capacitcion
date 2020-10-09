from datetime import datetime
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import UserError


CURP_LENGHT = 18
CLABE_LENGHT = 18
ACCOUNT_NUMBER_LENGHT = 10


class ResPartner(models.Model):
    _inherit = 'res.partner'

    beneficiary_type_ids = fields.Many2many(
        'grp.expense.beneficiary.type.catalog', 'partner_id', 'beneficiary_type_id', help='Indicate the beneficiary '
        'types for this record.')
    account_number = fields.Char()
    bank_id = fields.Many2one('eaccount.bank', translate=True)
    bank_branch = fields.Char(translate=True)
    beneficiary_type_id = fields.Many2one('grp.expense.beneficiary.type.catalog', translate=True)
    between_streets = fields.Char(translate=True)
    country_id = fields.Many2one('res.country', translate=True)
    clabe = fields.Char(translate=True)
    date = fields.Date(default=datetime.today())
    house_number = fields.Integer(translate=True)
    is_beneficiary = fields.Boolean(translate=True)
    files_ids = fields.Many2many('ir.attachment', string="Add file", translate=True)
    key = fields.Char(translate=True)
    name = fields.Char(required=True, translate=True)
    payment_method_id = fields.Many2one(
        'eaccount.payment.methods',
        translate=True,
        readonly=False,
        default=lambda self: self.env['eaccount.payment.methods'].search([('name','=','Transferencia')], limit=1))
    social_reazon = fields.Char(translate=True)
    state_id = fields.Many2one(
        'res.country.state',
        translate=True,
        default=lambda self: self.env['res.country.state'].search([('name','=','Jalisco')], limit=1))
    beneficiary_status = fields.Selection(
        [('active', 'Active'),
         ('inactive', 'Inactive')],
        string="Status", translate=True)
    suburb_id = fields.Many2one('grp.expense.suburb.catalog', translate=True)
    town_id = fields.Many2one('grp.expense.town.catalog', translate=True)
    vat = fields.Char(required=True, translate=True)
    zip_id = fields.Many2one('grp.expense.zip.code.catalog', translate=True)
    account_payment_id = fields.Many2one(
        "pay.method", string="Forma de Pago",
    )

    @api.onchange('supplier')
    def _set_beneficiary_type_P01(self):
        if self.supplier:
            self.beneficiary_type_ids = self.env['grp.expense.beneficiary.type.catalog'].search([('key','=','P01')])

    @api.constrains('curp')
    def _check_curp_character_quantity(self):
        for record in self:
            if record.curp:
                if len(record.curp) != CURP_LENGHT:
                    raise exceptions.ValidationError(_("Curp must have 18 characters"))

    @api.constrains('curp')
    def _check_curp_characters_only(self):
        for record in self:
            if record.curp:
                if not record.curp.isalnum(): raise exceptions.ValidationError(_("Curp must have only letters and numbers"))

    @api.constrains('clabe')
    def _check_clabe_character_quantity(self):
        for record in self:
            if record.clabe:
                if len(record.clabe) != CLABE_LENGHT:
                    raise exceptions.ValidationError(_("Clabe must have 18 characters"))

    @api.constrains('clabe')
    def _check_clabe_characters_only(self):
        for record in self:
            if record.clabe:
                if not record.clabe.isnumeric(): raise exceptions.ValidationError(_("Clabe must have only numbers"))

    @api.constrains('account_number')
    def _check_account_number_character_quantity(self):
        for record in self:
            if record.account_number:
                if len(record.account_number) != ACCOUNT_NUMBER_LENGHT:
                    raise exceptions.ValidationError(_("Account number must have 10 characters"))

    @api.constrains('account_number')
    def _check_account_number_characters_only(self):
        for record in self:
            if record.account_number:
                if not record.account_number.isnumeric(): raise exceptions.ValidationError(_("Account number must have only numbers"))

    @api.constrains('phone','mobile')
    def _only_numberic_values(self):
        for record in self:
            if record.phone:
                if not record.phone.isdigit():
                    raise exceptions.ValidationError(_("The phone should contain only numbers"))
            if record.mobile:
                if not record.mobile.isdigit():
                    raise exceptions.ValidationError(_("The mobile should contain only numbers"))

    @api.multi
    def unlink(self):
        beneficiary_type = self.env.ref('grp_expense.beneficiary_type_z01')
        if self.filtered(lambda rec: beneficiary_type in rec.beneficiary_type_ids):
            raise UserError(_(
                'No es posible eliminar un beneficiario con el tipo Otros, en su lugar puede desactivarlo.'))
        return super(ResPartner, self).unlink()
