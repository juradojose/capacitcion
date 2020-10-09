# -*- coding: utf-8 -*-

import base64
from codecs import BOM_UTF8
from lxml import objectify
from suds.client import Client
from odoo.osv import osv
from odoo.tools.float_utils import float_is_zero
from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo.exceptions import UserError


class WizardLoadXML(models.TransientModel):
    _name = "wizard.load.xml"
    _description = "Cargar XML"

    date = fields.Date(string="Fecha", default=fields.Date.context_today,)
    user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user
    )
    dragndrop = fields.Char(help='Field to upload files')

    def get_impuestos(self, xml):
        if not hasattr(xml, 'Impuestos'):
            return {}
        taxes_list = {'wrong_taxes': [], 'taxes_ids': []}
        taxes_xml = xml.Impuestos
        taxes = []

        if hasattr(taxes_xml, 'Traslados'):
            taxes = self.collect_taxes(taxes_xml.Traslados.Traslado)
        if hasattr(taxes_xml, 'Retenciones'):
            taxes += self.collect_taxes(taxes_xml.Retenciones.Retencion)

        for tax in taxes:
            tax_group_id = self.env['account.tax.group'].search(
                [('name', '=', tax['tax'])], limit=1)
            domain = [('tax_group_id', 'in', tax_group_id.ids),
                      ('type_tax_use', '=', 'purchase')]

            name = ''
            if 'RET' not in tax['tax'] or tax['rate']:
                domain += [('amount', '=', tax['rate'])]
                name = '%s(%s%%)' % (tax['tax'], tax['rate'])

            tax_get = self.env['account.tax'].search(domain, limit=1)

            if not tax_group_id or not tax_get:
                taxes_list['wrong_taxes'].append(
                    '%s(%s%%)' % (tax['tax'], tax['rate']))
            else:
                tax['id'] = tax_get.id
                tax['account'] = tax_get.account_id.id
                tax['name'] = name if name else tax['tax']
                taxes_list['taxes_ids'].append(tax)
        return taxes_list

    @api.model
    def check_xml(self, xml64, key):
        """Validate that attributes in the XML before create invoice
        or attach.
        :param str xml64: The CFDI in base64
        :param str key: Is the document name
        :return: A dictionary with the next attributes
            - key.- If all is OK return True, else False
            - xml64.- The same CFDI in base64
            - where.- The process that was executed
            - error.- If is found, return the message
            - invoice_id.- The invoice realated
        :rtype: dict
        """
        inv_id = self.env.context.get('active_id', [])
        inv_obj = self.env['account.invoice']
        inv = inv_obj.browse(inv_id)
        try:
            xml_str = base64.decodestring(xml64.replace(
                'data:text/xml;base64,', '')).lstrip(BOM_UTF8)
            xml = objectify.fromstring(xml_str)
            xml_vat_emitter = xml.Emisor.get('Rfc', '').upper()
            xml_vat_receiver = xml.Receptor.get('Rfc', '').upper()
            xml_amount = xml.get('Total', 0.0)
            xml_uuid = inv.l10n_mx_edi_get_tfd_etree(xml).get('UUID', '')
            xml_folio = xml.get('Folio', '')
            xml_currency = xml.get('Moneda', 'MXN')
            xml_taxes = self.get_impuestos(xml)
            xml_discount = float(xml.get('Descuento', '0.0'))
            xml_name_supplier = xml.Emisor.get('Nombre', '')
            version = xml.get('Version')
        except (AttributeError, SyntaxError) as exce:
            return {key: False, 'xml64': xml64, 'where': 'CheckXML',
                    'error': [exce.__class__.__name__, str(exce)]}

        validate_xml = self.validate_xml_sat(xml_uuid, xml_amount, xml_vat_emitter, xml_vat_receiver)
        inv_vat_receiver = (
            self.env.user.company_id.vat or '').upper()
        inv_vat_emitter = (inv.commercial_partner_id.vat or '').upper()
        inv_amount = inv.amount_total or 0.0
        inv_folio = inv.reference or ''
        exist_supplier = self.env['res.partner'].search(
            [('vat', '=', xml_vat_emitter)], limit=1)
        exist_reference = xml_folio and inv_obj.search(
            [('reference', '=', xml_folio),
             ('partner_id', '=', exist_supplier.id)], limit=1)
        uuid_dupli = inv.search([
            ('cfdi_folio_fiscal', '=', xml_uuid), ('id', '!=', inv.id)],
            limit=1)
        mxns = ['mxp', 'mxn', 'pesos', 'peso mexicano', 'pesos mexicanos']
        xml_currency = 'MXN' if xml_currency.lower() in mxns else xml_currency

        exist_currency = self.env['res.currency'].search(
            [('name', '=', xml_currency)], limit=1)
        error = [
            (not xml_uuid, {'signed': True}),
            (validate_xml == 'Cancelado', {'cancel': True}),
            ((xml_uuid and uuid_dupli), {'uuid_duplicate': (
                uuid_dupli.partner_id.name, uuid_dupli.reference)}),
            ((inv_vat_receiver != xml_vat_receiver),
             {'rfc': (xml_vat_receiver, inv_vat_receiver)}),
            ((not inv_id and exist_reference),
             {'reference': (xml_name_supplier, xml_folio)}),
            ((version != '3.3' and xml_discount), {'discount': True}),
            ((not inv_id and not exist_supplier),
             {'supplier': xml_name_supplier}),
            ((not inv_id and xml_currency and not exist_currency),
             {'currency': xml_currency}),
            ((not inv_id and xml_taxes.get('wrong_taxes', False)),
             {'taxes': xml_taxes.get('wrong_taxes', False)}),
            ((inv_id and inv_folio != xml_folio),
             {'folio': (xml_folio, inv_folio)}),
            ((inv_id and inv_vat_emitter != xml_vat_emitter), {
                'rfc_supplier': (xml_vat_emitter, inv_vat_emitter)}),
            ((inv_id and not float_is_zero(float(inv_amount)-float(
                xml_amount), precision_digits=2)), {
                    'amount': (xml_amount, inv_amount)})
        ]
        msg = {}
        for e in error:
            if e[0]:
                msg.update(e[1])
        if msg:
            msg.update({
                key: False,
                'xml64': xml64,
                'allow_create_supplier': self.env.user.company_id.allow_create_expense_suppliers,
            })
            return msg

        if not inv_id:
            invoice_status = self.create_invoice(
                xml, exist_supplier, exist_currency)
            if invoice_status.get('key', False):
                del invoice_status['key']
                invoice_status.update({key: True})
                return invoice_status

            del invoice_status['key']
            invoice_status.update({key: False, 'xml64': xml64})
            return invoice_status

        inv.write({'cfdi_folio_fiscal': xml_uuid})
        return {key: True, 'invoice_id': inv.id}

    def validate_company(self, vat):
        if vat != self.env.user.company_id.vat:
            return False

    @api.model
    def create_partner(self, xml64, key=False):
        """ It creates the supplier dictionary, getting data from the XML
        Receives an xml decode to read and returns a dictionary with data """
        # Default Mexico because only in Mexico are emitted CFDIs
        try:
            # Fix the CFDIs emitted by the SAT
            xml = objectify.fromstring(base64.decodestring(xml64.replace(
                'data:text/xml;base64,', '')).lstrip(BOM_UTF8))

        except BaseException as exce:
            return {
                key: False, 'xml64': xml64, 'where': 'CreatePartner',
                'error': [exce.__class__.__name__, str(exce)]}

        rfc_emitter = xml.Emisor.get('Rfc', False)
        name = xml.Emisor.get('Nombre', rfc_emitter)
        xml_currency = xml.get('Moneda', 'MXN')

        # check if the partner exist from a previos invoice creation
        partner_domain = ['|', ('name', '=', name), ('vat', '=', rfc_emitter)]
        partner_obj = self.env['res.partner'].sudo()
        currency_obj = self.env['res.currency'].sudo()
        currency_field = 'property_purchase_currency_id' in partner_obj._fields
        if currency_field:
            currency_id = currency_obj.search(
                [('name', '=', xml_currency)], limit=1)
            partner_domain.append(
                ('property_purchase_currency_id', '=', currency_id.id))
        partner = self._get_partner_cfdi(partner_domain)
        if not partner and currency_field:
            partner_domain.pop()
            partner = self._get_partner_cfdi(partner_domain)

        if partner:
            return self.check_xml(xml64, key)

        partner = self.env['res.partner'].create({
            'name': name,
            'company_type': 'company' if len(rfc_emitter) == '12' else 'person',
            'vat': rfc_emitter,
            'country_id': self.env.ref('base.mx').id,
            'supplier': False,
            'customer': False,
            'category_id': [(6, 0, self.env.ref('grp_expense.tag_expenses').ids)],
            'beneficiary_type_ids': [(6, 0, self.env.ref('grp_expense.beneficiary_type_z01').ids)],
            'expense_support': True,
        })
        msg = _('This partner was created when invoice %s%s was added from '
                'a XML file. Please verify that the datas of partner are '
                'correct.') % (xml.get('Serie', ''), xml.get('Folio', ''))
        partner.message_post(subject=_('Info'), body=msg)
        return self.check_xml(xml64, key)

    @api.multi
    def _get_partner_cfdi(self, domain):
        """Consider in the search the next order:
            - Is supplier
            - Is company
            - Any record with the same VAT received."""
        partner = self.env['res.partner']
        domain.append(('supplier', '=', True))
        domain.append(('is_company', '=', True))
        cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        return cfdi_partner

    @api.multi
    def create_invoice(self, xml, supplier, currency_id):
        """ Create supplier invoice from xml file
        :param xml (element) : xml file with the datas of purchase
        supplier (object): (res.partner) supplier partner
        currency_id (object): (res.currency) payment currency of the purchase
        :return (dict):
        """
        inv_obj = self.env['account.invoice']
        line_obj = self.env['account.invoice.line']
        journal = inv_obj.with_context(type='in_invoice')._default_journal()
        prod_obj = self.env['product.product']
        # sat_code_obj = self.env['l10n_mx_edi.product.sat.code']
        uom_obj = uom_obj = self.env['product.uom']
        default_account = line_obj.with_context({
            'journal_id': journal.id, 'type': 'in_invoice'})._default_account()
        invoice_line_ids = []
        msg = (_('Some products are not found in the system, and the account '
                 'that is used like default is not configured in the journal, '
                 'please set default account in the journal '
                 '%s to create the invoice.') % journal.name)

        try:
            date_inv = xml.get('Fecha', '').split('T')
            uuid = inv_obj.l10n_mx_edi_get_tfd_etree(xml).get('UUID', '')
            for rec in xml.Conceptos.Concepto:
                name = rec.get('Descripcion', '')
                no_id = rec.get('NoIdentificacion', name)
                uom = rec.get('Unidad', '')
                # uom_code = rec.get('ClaveUnidad', '')
                qty = rec.get('Cantidad', '')
                price = rec.get('ValorUnitario', '')
                amount = rec.get('Importe', '0.0')
                product_id = prod_obj.search([
                    '|', ('default_code', '=ilike', no_id),
                    ('name', '=ilike', name)], limit=1)
                account_id = (
                    product_id.property_account_expense_id.id or product_id.
                    categ_id.property_account_expense_categ_id.id or
                    default_account)

                if not account_id:
                    return {
                        'key': False, 'where': 'CreateInvoice',
                        'error': [
                            _('Account to set in the lines not found.<br/>'),
                            msg]}

                discount = 0.0
                if rec.get('Descuento') and amount:
                    discount = (float(rec.get('Descuento', '0.0')) / float(
                        amount)) * 100

                domain_uom = [('name', '=ilike', uom)]
                line_taxes = [tax['id'] for tax in
                              self.get_impuestos(rec).get('taxes_ids', [])]

                uom_id = uom_obj.with_context(
                    lang='es_MX').search(domain_uom, limit=1)

                invoice_line_ids.append((0, 0, {
                    'product_id': product_id.id,
                    'account_id': account_id,
                    'name': name,
                    'quantity': float(qty),
                    'uom_id': uom_id.id,
                    'invoice_line_tax_ids': [(6, 0, line_taxes)],
                    'price_unit': float(price),
                    'discount': discount,
                }))

            usage = self.env['catalogo.usocfdi'].search([('usocfdi', '=', xml.Receptor.get('UsoCFDI'))], limit=1)
            fiscalyear = self.env['account.fiscalyear'].search([('code', '=', date_inv[0][:4])])
            invoice_id = inv_obj.with_context(ejercicio=fiscalyear).create({
                'partner_id': supplier.id,
                'usocfdi': usage.id,
                'reference': self.get_xml_folio(xml) or uuid,
                'currency_id': (
                    currency_id.id or self.env.user.company_id.currency_id.id),
                'invoice_line_ids': invoice_line_ids,
                'type': 'in_invoice',
                'cfdi_folio_fiscal': uuid,
                'journal_id': journal.id,
                'l10n_mx_edi_cfdi_amount': xml.get('Total'),
                'date_invoice': date_inv[0],
                'date_due': False,
                'name': self.get_xml_folio(xml),
            })
            invoice_id.l10n_mx_edi_update_sat_status()

            return {'key': True, 'invoice_id': invoice_id.id}
        except BaseException as exce:
            return {
                'key': False, 'where': 'CreateInvoice',
                'error': [exce.__class__.__name__, str(exce)]}

    def get_xml_folio(self, xml):
        return '%s%s' % (xml.get('Serie', ''), xml.get('Folio', ''))

    def validate_xml_sat(self, xml_uuid, monto_total, rfc_emisor, rfc_receptor):
        url = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl"
        try:
            client = Client(url)
        except:
            raise UserError(_(
                u"No se pudo establecer la conexión con el sitio del SAT para validar la factura, por favor revise su conexión de internet y/o espere a que el sitio del SAT se encuentre disponible..."))  # noqa
        if not xml_uuid:
            raise osv.except_osv(
                "Formato de archivo XML incorrecto",
                u'Se necesita cargar un archivo de extensi\xf3n ".xml" (CFDI)',
            )
        result = client.service.Consulta(
            """"?re=%s&rr=%s&tt=%s&id=%s"""
            % (rfc_emisor, rfc_receptor, monto_total, xml_uuid)
        )
        return result

    @staticmethod
    def collect_taxes(taxes_xml):
        """ Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data
        :rtype: list
        """
        taxes = []
        tax_codes = {'001': 'ISR', '002': 'IVA', '003': 'IEPS'}
        for rec in taxes_xml:
            tax_xml = rec.get('Impuesto', '')
            tax_xml = tax_codes.get(tax_xml, tax_xml)
            amount_xml = float(rec.get('Importe', '0.0'))
            rate_xml = float_round(
                float(rec.get('TasaOCuota', '0.0')) * 100, 4)
            if 'Retenciones' in rec.getparent().tag:
                tax_xml = tax_xml
                amount_xml = amount_xml * -1
                rate_xml = rate_xml * -1

            taxes.append({'rate': rate_xml, 'tax': tax_xml,
                          'amount': amount_xml})
        return taxes
