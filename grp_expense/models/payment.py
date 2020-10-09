# -*- coding: utf-8 -*-

from datetime import datetime
import base64
from io import BytesIO
from tempfile import TemporaryFile
import openpyxl
import xlsxwriter
import num2words
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class MomentosPresupuestalesGasto(models.Model):
    _inherit = "account.momentospresupuestales"

    expense_payment_id = fields.Many2one("expense.payment", string="Solicitud de pago")


class ApoyosSociales(models.Model):
    _name = "beneficiarios.apoyos.sociales"
    _description = (
        "Carga de layout con información de beneficiarios para apoyos sociales"
    )

    num = fields.Integer(string="Num")
    cuenta = fields.Integer(string="Cuenta")
    importe = fields.Float(string="Importe")
    clave = fields.Integer(string="Clave")
    nombre = fields.Char(string="Nombre")
    referencia = fields.Char(string="Referencia")
    concepto = fields.Char(string="Concepto de Pago")
    num_proyec = fields.Integer(string="Número de Proyecto")
    generacion = fields.Integer(string="Generacion")
    payment_id = fields.Many2one("expense.payment", string="Apoyos")
    documento = fields.Binary(string="Cargar")

    def create_lines(self):
        for record in self:
            file = record.documento.decode("base64")
            excel_fileobj = TemporaryFile("wb+")
            excel_fileobj.write(file)
            excel_fileobj.seek(0)

            # Create workbook
            workbook = openpyxl.load_workbook(excel_fileobj, data_only=True)
            # Get the first sheet of excel file
            sheet = workbook[workbook.get_sheet_names()[0]]

            # Iteration on each rows in excel
            cont = 0
            for row in sheet.rows:
                if cont > 0:
                    num = row[0].value
                    cuenta = row[1].value
                    importe = row[2].value
                    clave = row[3].value
                    nombre = row[4].value
                    referencia = row[5].value
                    concepto = row[6].value
                    num_pro = row[7].value
                    generacion = row[8].value

                    data = {
                        "num": num,
                        "cuenta": cuenta,
                        "importe": importe,
                        "clave": clave,
                        "nombre": nombre,
                        "referencia": referencia,
                        "concepto": concepto,
                        "num_proyec": num_pro,
                        "generacion": generacion,
                        "payment_id": record.payment_id.id,
                    }
                    self.env["beneficiarios.apoyos.sociales"].create(data)
                cont = cont + 1

            self.env.cr.execute(
                "DELETE FROM beneficiarios_apoyos_sociales WHERE cuenta is null and importe is null and clave is null and num_proyec is null"
            )


class Clasificadores(models.Model):
    _name = "catalogo.clasificadores"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    name = fields.Char("Nombre", required=True, track_visibility="always")
    codigo = fields.Char(string="Código")
    date = fields.Date(
        string="Fecha de Registro",
        track_visibility="onchange",
        default=fields.Date.today,
    )
    status = fields.Char(
        compute="_status_act", string="Estado", track_visibility="always"
    )
    active = fields.Boolean(default=True)

    @api.model
    def onchange_case(self, name):
        if name:
            result = {"value": {"name": str(name.encode("utf-8")).upper()}}
            return result

    @api.depends("active")
    def _status_act(self):
        for location in self:
            if location.active == True:
                location.status = "Activo"
            if location.active == False:
                location.satus = "Inactivo"

    @api.constrains("name")
    def check_fields(self):
        exceptions = False
        if self.name:
            if (
                len(self.search(["&", ("name", "=", self.name), ("id", "!=", self.id)]))
                > 0
            ):
                raise exceptions.ValidationError(
                    "El nombre ya existe favor de ingresar uno distinto"
                )


class ExpensePayment(models.Model):
    _name = "expense.payment"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    def conv(self, val):
        return num2words.num2words(val, lang="es")

    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id

    clasificador = fields.Many2one(
        "catalogo.clasificadores",
        string="Clasificación",
        track_visibility="onchange",
        placeholder="Ninguno",
    )
    date = fields.Date(
        string="Fecha de emisión",
        track_visibility="onchange",
        default=fields.Date.today,
    )
    date_expired = fields.Date(
        string="Fecha de Vencimiento", track_visibility="onchange"
    )
    informes_general = fields.Char(
        string="Informes", track_visibility="onchange"
    )
    date_payment = fields.Date(string="Fecha Prob Pago")
    name = fields.Char(string="No. Solicitud")
    picking_id = fields.Many2one(
        "stock.picking", string="Recibo de Materiales y Servicios",
    )
    po_id = fields.Many2one(
        "purchase.order",
        string="OC",
        track_visibility="onchange",
        readonly=True,
        related="picking_id.purchase_id",
    )
    partner_alternate_id = fields.Many2one("res.partner", string="Beneficiario alterno")
    puesto_partner = fields.Many2one(
        "hr.job", string="Puesto", related="partner_id.job_id"
    )
    dependence_id = fields.Many2one("hr.department", string="Dependencia", store=True)
    unit_responsible = fields.Char(
        string="Unidad Responsable (UR)",
        readonly=True,
        related="picking_id.unit_responsable",
    )
    dependence_ur_id = fields.Many2one("cri.concepto", string="Departamento (UEG")
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("to_authorize", "Por Autorizar"),
            ("first_authorization", "Primera autorización"),
            ("second_authorization", "Segunda autorización"),
            ("received", "Recibida"),
            ("in_review", "En revisión"),
            # ("in_review2", "En revisión"),
            ("revised", "Revisada"),
            ("validated", "Validada"),
            ("authorized", "Autorizada"),
            ("shipping_box", "Envío a Caja"),
            ("rejected", "Cancelada"),
            ("observed", "Observada"),
            ("entregado_caja", "Recibido en Caja"),
            ("scheduled", "Programado"),
            ("create_check", "Crear Cheque"),
            ("sent", "Enviado"),
            ("paid", "Pagado"),
            ("env_sop", "Enviado a Soporte del Gasto"),
            ("env_cont", "Enviado a Contabilidad"),
            ("frozen", "Congelado"),
            ("printed", "Impreso"),
        ],
        track_visibility="onchange",
        default="draft",
    )
    type_affectation_id = fields.Many2one(
        "grp_account.affectation.type",
        string="Tipo de afectación",
        compute="_eventos_contables",
        store=True,
    )
    user_id = fields.Many2one("res.users", string="Asignado a")
    depedence_id = fields.Many2one(
        "hr.department", string="Dependencia", compute="_eventos_contables",domain="[('nivel_id.codigo', '=', '5')]", store=True
    )
    depedence_ueg_id = fields.Many2one(
        "hr.department",
        string="Departamento (UEG)",
        compute="_eventos_contables",domain="[('nivel_id.codigo', '=', '6'), ('parent_id', '=', depedence_id)]",
        store=True,
    )
    source_finantial_id = fields.Many2one(
        "recaudador.fuentesfinanciamiento",
        string="Origen (de los recursos)",
        compute="_eventos_contables",
        store=True,
    )
    number_doc = fields.Char(string="No. Oficio", size=20)
    application_concept = fields.Char(string="Concepto de Solicitud")
    expense_type = fields.Char(string="Tipo de Gasto")
    state_previous = fields.Char(string="Estatus anterior")
    previous_counterreceipt = fields.Integer(string="No. CR anterior")
    date_previous = fields.Date(
        string="Fecha de CR", readonly=True, related="picking_id.date_order",
    )
    picking_id = fields.Many2one(
        "stock.picking", string="Recibo de Materiales y Servicios"
    )

    def _justificacion_default(self):
        if self.event_general:
            justificacion = (
                self.env["model.cont.eventos"]
                .search([("general_event_id", "=", self.event_general.id)])
                .id
            )
            return justificacion

    justification_id = fields.Many2one(
        "justification.catalog",
        string="Justificación Presupuestal",
        compute="_eventos_contables",
        store=True,
    )
    event_general = fields.Many2one("model.cont.eventos", string="Evento General",)
    details_view = fields.Selection(related="event_general.details_view",store=True)
    encabezado_view = fields.Selection(related="event_general.encabezado_view",store=True)
    solicitud_pago = fields.Boolean("Solicitud de Pago",related="event_general.solicitud_pago")
    recibo = fields.Boolean("Recibo",related="event_general.recibo")
    carta_aceptacion = fields.Boolean("Reporte Carta de Aceptacion",related="event_general.carta_aceptacion")
    contrarecibo = fields.Boolean("Contrarecibo",related="event_general.contrarecibo")
    reporte_devoluciones = fields.Boolean("Reporte Devoluciones",related="event_general.reporte_devoluciones")
    layout_beneficarios = fields.Boolean("Layout",related="event_general.layout_beneficarios")
    informe = fields.Boolean("Informes",related="event_general.informe")
    fecha_vencimiento = fields.Boolean("Fecha Vencimiento",related="event_general.fecha_vencimiento")
    comprobacion_gastos = fields.Boolean("Comprobación de Gastos",related="event_general.comprobacion_gastos")
    specific_cluster = fields.Many2one(
        "grp_account.accounting.grouper",
        string="Agrupador Especifico",
        compute="_eventos_contables",
        store=True,
    )
    general_grouter = fields.Many2one(
        "grp_account.accounting.grouper",
        string="Agrupador Genérico",
        compute="_eventos_contables",
        store=True,
    )
    partner_id = fields.Many2one(
        "hr.employee", string="Beneficiario", track_visibility="onchange"
    )
    bias = fields.Boolean(
        string="Parcialidad", readonly=True, related="picking_id.bias",
    )
    number_bias = fields.Char(
        string="No. de Parcialidad de OC",
        readonly=True,
        related="picking_id.number_bias",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        readonly=True,
        default=_default_currency,
        track_visibility="always",
    )
    total_invoice = fields.Monetary(
        string="Total de Factura",
        related="picking_id.total_invoice",
        readonly=True,
        currency_field="currency_id",
    )
    total = fields.Float(string="Importe", compute="_compute_total", readonly=True)
    total_pivot = fields.Float(
        string="Total Solicitudes", compute="_eventos_contables", store=True
    )
    balance_oc = fields.Float(
        string="Saldo de OC", related="picking_id.balance_oc", readonly=True,
    )
    detail_ids = fields.One2many(
        "expense.payment.detail", "payment_id", string="Detalle",
    )
    detail_ids_AF = fields.One2many(
        "expense.payment.detail", "payment_af_id", string="Detalle",
    )
    detail_ids_di = fields.One2many(
        "expense.payment.detail", "payment_di_id", string="Detalle",
    )
    detail_ids_PD = fields.One2many(
        "expense.payment.detail", "payment_pd_id", string="Detalle",
    )
    detail_ids_FF = fields.One2many(
        "expense.payment.detail", "payment_ff_id", string="Detalle",
    )
    detail_ids_SP = fields.One2many(
        "expense.payment.detail", "payment_sp_id", string="Detalle",
    )
    apoyos_sociales = fields.One2many(
        "beneficiarios.apoyos.sociales", "payment_id", string="Apoyos",
    )
    documents_ids = fields.One2many(
        "expense.payment.documents", "payment_id", string="Docuemntos",
    )
    beneficiary_ids = fields.One2many(
        "expense.payment.beneficiary", "payment_id", string="Datos Bancarios",
    )
    beneficiary_ids_FF = fields.One2many(
        "expense.payment.beneficiary", "payment_id", string="Datos Bancarios",
    )
    binnacle_ids = fields.One2many(
        "binnacle.state.payment", "expense_id", string="Bitácora",
    )
    tipo_beneficiario = fields.Many2one(
        "grp.expense.beneficiary.type.catalog", string="Tipo Beneficiario", default=lambda self: self.env["grp.expense.beneficiary.type.catalog"].search([("key", "=", "F01")])
    )
    solicitante = fields.Many2one(
        "res.users",
        string="Solicitante",
        default=lambda self: self.env.user
    )
    code_justificacion = fields.Char(
        string="Codigo justificación", compute="_eventos_contables", store=True
    )
    code_evento = fields.Char(
        string="Codigo evento", compute="_eventos_contables", store=True
    )
    code_clasificacion = fields.Char(
        string="Codigo clasificacion", related="clasificador.codigo"
    )
    suma_total_AF = fields.Float("Total", compute="_suma_detalle_line")
    suma_total_PD = fields.Float("Total", compute="_suma_detalle_line")
    suma_line_FF = fields.Float("Total", compute="_suma_detalle")
    impuestos_ff = fields.Float("Impuestos", compute="_suma_detalle")
    importe_sp = fields.Float(
        string="Importe SP"
    )
    total_comprobado = fields.Float(
        string="Total Comprobado", compute="_eventos_contables", store=True
    )
    total_faltante = fields.Float(
        string="Saldo", compute="_eventos_contables", store=True
    )
    importe_sp_FF = fields.Float(
        string="Importe SP", compute="_eventos_contables", store=True
    )

    reintegro = fields.Float(string="Reintengro", compute="_suma_detalle")
    saldo = fields.Float(string="Saldo", compute="_suma_detalle")
    total_ff = fields.Float(string="Total", compute="_suma_detalle")
    comisionado_por = fields.Char(string="Comisionado por")
    destino = fields.Char(string="Destino (s)")
    asunto = fields.Char(string="Asunto (s)")
    periodo_inicial = fields.Date(string="Periodo inicial del viaje")
    periodo_final = fields.Date(string="Periodo final del viaje")
    observaciones = fields.Char(string="Observaciones")
    vehiculo = fields.Char(string="Vehículo")
    marca = fields.Char(string="Marca")
    sub_marca = fields.Char(string="Submarca")
    anio = fields.Char(string="Año")
    no_placas = fields.Char(string="No. placas")
    cilindros = fields.Char(string="Cilindros")
    account_payment_id = fields.Many2one("pay.method", string="Forma de Pago",related="beneficiary_ids.account_payment_id")
    partner_bank = fields.Many2one("res.partner.bank", string="Nombre de la cuenta", related="beneficiary_ids.partner_bank")
    bank_id = fields.Many2one("res.bank", string="Banco", related="partner_bank.bank_id")
    bank_account = fields.Char(string="Cuenta Bancaria", related="partner_bank.acc_number")
    clabe = fields.Char(string="CLABE", related="partner_bank.clabe",)
    code = fields.Char(string="Forma de pago code", related="account_payment_id.code")
    avoid_duplicate_check = fields.Boolean()

    momentos_ids = fields.One2many(
        "account.momentospresupuestales",
        "expense_payment_id",
        "Momentos Presupuestales",
    )
    cadena = fields.Selection(
        [("cadena", "Cadenas Productivas"),], track_visibility="onchange"
    )
    compromiso = fields.Many2one(
        "budget.commitment", string="Compromiso Presupuestario",domain="[('state','=','done')]"
    )
    no_programa = fields.Char(
        string="Descripción del Compromiso", readonly=True, related="compromiso.name"
    )
    desc_programa = fields.Char(string="Descripción Programa", readonly=True)
    no_pago = fields.Selection(
        [
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
            ("5", "5"),
            ("6", "6"),
            ("7", "7"),
            ("8", "8"),
            ("9", "9"),
            ("10", "10"),
            ("11", "11"),
            ("12", "12"),
        ],
        track_visibility="onchange",
        string="No. de Pago",
    )
    solicitud_general = fields.Boolean(string="Solicitud General")
    compromisos_presupuestarios = fields.Boolean(
        string="Compromisos Presupuestarios", default=True
    )
    pagar_por = fields.Selection(
        [("1", "Cadenas Productivas"),], track_visibility="onchange", string="Pagar por"
    )
    comprobacion_factura = fields.Many2one("account.invoice", string="Factura")
    #para generación de account.move
    line_ids = fields.One2many(
        comodel_name = 'expense.payment.line',
        inverse_name = 'payment_id',
        string = 'Detalle',
    )
    move_ids = fields.One2many(
        string = 'Account moves',
        comodel_name = 'account.move',
        inverse_name = 'expense_payment_id',
    )
    no_nota_credito = fields.Integer(string="No.nota de crédito")
    amparo_folio = fields.Char(string="Amparo/Folio")
    company_id = fields.Many2one('res.company', string='Company', required=True,default=lambda self: self.env.user.company_id)
    anios_anteriores = fields.Boolean("Filtro años anteriores",related="event_general.anios_anteriores")

    @api.onchange("event_general","date")
    def nota_credito_filtro(self):
        if self.anios_anteriores:
            fecha=self.ejercicio_id.name
            aniocobro=int(fecha)-1
            return {
                "domain": {
                    "nota_credito": [
                        ("aniocobros", "=", aniocobro),
                    ],
                }
            }
        else:
            return {
                "domain": {
                    "nota_credito": [
                        ("aniocobros", "=", self.ejercicio_id.name),
                    ],
                }
            }

    @api.onchange("event_general","date")
    def dependencia_beneficiario_filtro(self):
        if self.encabezado_view == "type2":
            return {
            "domain": {
                    "partner_id": [
                        ("department_id.parent_id", "=", self.depedence_id.id),
                        ("department_id", "=", self.depedence_ueg_id.id),
                        (
                        "address_home_id",
                        "in",
                        self.env["res.partner"]
                        .search(
                            [("beneficiary_type_ids", "in", self.tipo_beneficiario.ids)]
                        )
                        .ids,
                    )
                    ],
                }
            }
        else:
            return {
                "domain": {
                    "partner_id": [
                        ("department_id.parent_id", "=", self.depedence_id.id),
                        ("department_id", "=", self.depedence_ueg_id.id),
                    ],
                }
            }

    @api.multi
    @api.constrains(
        "state",
        "detail_ids",
        "detail_ids_AF",
        "detail_ids_PD",
        "detail_ids_FF",
        "detail_ids_SP",
        "beneficiary_ids",
        "picking_id"
    )
    def fnc_check_line(self):
        for record in self:
            if record.compromiso:
                if (
                len(record.search(["&", ("compromiso", "=", record.compromiso.id), ("id", "!=", record.id)]))
                    > 0
                ):
                    raise ValidationError(
                        "Ya existe ese compromiso en otro registro"
                    )

            if record.nota_credito:
                if (
                len(record.search(["&", ("nota_credito", "=", record.nota_credito.id), ("id", "!=", record.id)]))
                    > 0
                ):
                    raise ValidationError(
                        "Ya existe esa nota en otro registro"
                    )

            if record.po_id.id:
                record.depedence_id = record.picking_id.department_id.id
                record.depedence_ueg_id = record.picking_id.department_id.id
            if record.event_general.comprobacion_gastos and record.total_faltante<0:
                raise ValidationError(
                    """No se puede completar el registro debido a que el monto ya fue comprobado, favor de utilizar el evento general de Deudores con Saldo a Favor.
                                          """
                    % ()
                )
            if record.solicitud:
                record.partner_id=record.solicitud.partner_id
                record.tipo_beneficiario=record.solicitud.tipo_beneficiario

            if not record.beneficiary_ids and self.encabezado_view in ["type6"] and self.state not in ["draft","to_authorize"]:
                raise ValidationError(
                    """No se puede completar el registro debido a que no se encontro una forma de pago.
                                          """
                    % ()
                )
            if self.encabezado_view == "type6" and self.state not in ["draft","to_authorize"]:
                if not record.detail_ids_di:
                    raise ValidationError(
                        """No se puede completar el registro debido a que no se encontraron detalles.
                                              """
                        % ()
                    )
            if not record.beneficiary_ids and self.encabezado_view not in ["type6"]:
                raise ValidationError(
                    """No se puede completar el registro debido a que no se encontro una forma de pago.
                                          """
                    % ()
                )
            if (
                self.encabezado_view not in ["type2", "type3", "type4", "type5","type6","type7"]
            ):
                if not record.detail_ids and record.state not in ('draft','to_authorize'):
                    raise ValidationError(
                        """No se puede completar el registro debido a que no se encontraron detalles.
                                              """
                        % ()
                    )
            if self.encabezado_view == "type2":
                if not record.detail_ids_AF:
                    raise ValidationError(
                        """No se puede completar el registro debido a que no se encontraron detalles.
                                              """
                        % ()
                    )
            if self.encabezado_view == "type5":
                if not record.detail_ids_PD:
                    raise ValidationError(
                        """No se puede completar el registro debido a que no se encontraron detalles.
                                              """
                        % ()
                    )
            if not self.comprobacion_factura:
                if (self.encabezado_view in ["type3" ,"type4"]):
                    if record.detail_ids_FF or record.detail_ids_PD:
                        continue
                    else:
                        raise ValidationError(
                            """No se puede completar el registro debido a que no se encontraron detalles.
                                                  """
                            % ()
                        )
            if self.encabezado_view == "type7":
                if record.detail_ids_AF or record.detail_ids_FF or record.detail_ids_di:
                    continue
                else:
                    raise ValidationError(
                        """No se puede completar el registro debido a que no se encontraron detalles.
                                              """
                        % ()
                    )

            if len(self.beneficiary_ids.ids)>1:
                raise ValidationError(
                            """No se puede tener más de una forma de pago.
                                                  """
                            % ()
                        )

    @api.onchange("comprobacion_factura","date")
    def facturas_almacen_digital(self):
        self.env.cr.execute("select coalesce(comprobacion_factura,0) from expense_payment_detail")
        facturas = self.env.cr.fetchall()
        facturas_array = []
        comprobacion = 0
        for x in facturas:
            comprobacion = x[0]
            facturas_array.append(str(x[0]))

        return {
            "domain": {
                "comprobacion_factura": [
                    ("type", "=", "in_invoice"),
                    ("state", "=", "validated"),
                    ("l10n_mx_edi_sat_status","=","valid"),
                    ("date_invoice",'>=',self.date),
                    ("id", "not in", facturas_array),
                ],
            }
        }

    @api.onchange("event_general")
    def ejercicio_evento_general(self):
        return {
            "domain": {
                "source_finantial_id": [
                    ("anio_id", "=", self.ejercicio_id.id),
                ],
            }
        }

    @api.multi
    def create_lines(self):
        self.apoyos_sociales.create_lines()

    @api.multi
    def cargar_detalle_factura(self):
        if self.comprobacion_factura:
            factura = self.env["expense.payment.detail"].search(
                [("comprobacion_factura", "=", self.comprobacion_factura.id)]
            )
            if factura:
                raise ValidationError('Ya existe esa factura en otro registro')
            for item in self.comprobacion_factura.invoice_line_ids:
                self.env["expense.payment.detail"].create(
                    {
                        "date": self.comprobacion_factura.date_invoice,
                        "name": item.name,
                        "comprobacion_factura": self.comprobacion_factura.id,
                        "justificacion_gasto": item.justification_expense,
                        "importe_presupuesto_disponible": item.estructura_id._presupuesto_disponible_anual(),
                        "importe_virtual_disponible": item.estructura_id._presupuesto_disponible_anual(),
                        "razon_social": self.comprobacion_factura.partner_id.name,
                        "product_id": item.product_id.id,
                        "code_item": item.product_id.default_code_readonly,
                        "cantidad_recibida": item.quantity,
                        "price_unit": item.price_unit,
                        "unidad_medida_id": item.product_id.uom_id.id,
                        "supplier_taxes_id": [
                            (4, tax.id, 0) for tax in item.product_id.supplier_taxes_id
                        ],
                        "impuestos": item.amount_tax,
                        "partidas_id": item.partidas_id.id,
                        "estructura_contable_ids": item.estructura_id.id,
                        "state_invoice": "invoice",
                        "subtotal": item.quantity * item.price_unit,
                        "total": item.price_total,
                        "payment_ff_id": self.id,
                    }
                )
            self.comprobacion_factura=""

    @api.onchange("picking_id")
    def _onchange_recibos(self):
        self.env.cr.execute("select coalesce(picking_id,0) from expense_payment")
        solicitudes = self.env.cr.fetchall()
        solicitudes_array = []
        picking_id = 0
        for x in solicitudes:
            picking_id = x[0]
            solicitudes_array.append(str(x[0]))
        return {
            "domain": {
                "picking_id": [
                    ("state", "=", "done"),
                    ("id", "not in", solicitudes_array),
                ],
            }
        }

    solicitud = fields.Many2one("expense.payment", string="Solicitud")
    nota_credito = fields.Many2one("nota.credito",string="Nota de crédito")

    @api.onchange("event_general", "solicitud", "details_view","date")
    def filtro_solicitud(self):
        if self.details_view == "type4":
            return {
                "domain": {"solicitud": [
                    ("details_view", "in", ["type3", "type2"]),
                    ("state","=","shipping_box"),
                    ("date",'<=',self.date)],}
            }

    @api.depends("state", "comp_count")
    def _compute_comprobacionesFF(self):
        for record in self:
            comp_obj = self.env["expense.payment"].search(
                [("solicitud", "=", record.id)]
            )

            record.comp_ids = comp_obj.ids
            record.comp_count = len(comp_obj)

    comp_count = fields.Integer(
        compute="_compute_comprobacionesFF", string="Comprobaciones", default=0
    )
    comp_ids = fields.Many2many(
        "expense.payment",
        compute="_compute_comprobacionesFF",
        string="Comprobaciones",
        copy=False,
    )

    @api.multi
    def action_imprimir_solicitud(self):
        return self.env["report"].get_action(self, "grp_expense.report_solicitud_pago")

    @api.multi
    def action_imprimir_recibo(self):
        return self.env["report"].get_action(self, "grp_expense.report_recibo")

    @api.multi
    def action_imprimir_contrarecibo(self):
        return self.env["report"].get_action(self, "grp_expense.report_contrarecibo")

    @api.multi
    def action_imprimir_carta(self):
        return self.env["report"].get_action(
            self, "grp_expense.report_carta_aceptacion"
        )

    @api.multi
    def action_imprimir_observaciones(self):
        return self.env["report"].get_action(self, "grp_expense.report_observaciones")

    @api.multi
    def action_view_comprobaciones(self):
        for record in self:
            comp_obj = 0
            comp_cancelados_obj = 0
            comp_obj = self.env["expense.payment"].search(
                [("solicitud", "=", record.id), ("encabezado_view", "=", "type3")]
            )
            comp_cancelados_obj = self.env["expense.payment"].search(
                [
                    ("solicitud", "=", record.id),
                    ("encabezado_view", "=", "type3"),
                    ("state", "=", "rejected"),
                ]
            )

            view_form = record.env.ref("grp_expense.view_expense_payment_form")
            view_tree = record.env.ref("grp_expense.view_expense_payment_tree")

            if len(comp_obj) == 0:
                return {
                    "name": ("Comprobaciones"),
                    "view_type": "form",
                    "type": "ir.actions.act_window",
                    "view_mode": "form",
                    "res_model": "expense.payment",
                    "view_id": self.env.ref("grp_expense.view_expense_payment_form").id,
                }
            elif len(comp_obj) == 1:

                return {
                    "name": ("Comprobaciones"),
                    "view_type": "form",
                    "type": "ir.actions.act_window",
                    "view_mode": "form",
                    "res_id": comp_obj.id,
                    "res_model": "expense.payment",
                    "view_id": self.env.ref("grp_expense.view_expense_payment_form").id,
                }
            else:
                return {
                    "type": "ir.actions.act_window",
                    "name": "Comprobaciones",
                    "view_type": "form",
                    "view_mode": "tree,form",
                    "views": [(view_tree.id, "tree"), (view_form.id, "form")],
                    "view_id": view_tree.id,
                    "res_model": "expense.payment",
                    "domain": [("solicitud", "=", record.id)],
                }

    @api.one
    def _suma_detalle_line(self):
        self.suma_total_AF = sum([line.total_af for line in self.detail_ids_AF])
        self.suma_total_PD = sum([line.total_af for line in self.detail_ids_PD])

    @api.multi
    @api.depends("date")
    def _presupuesto_compute(self):
        for record in self:
            presupuesto_obj = self.env["crossovered.budget"].search(
                [
                    ("state", "=", "done"),
                    ("plantipo", "=", "E"),
                    ("date_from", "<=", record.date),
                    ("date_to", ">=", record.date),
                ]
            )
            if presupuesto_obj:
                record.presupuesto_id = presupuesto_obj.id
                record.ejercicio_id = presupuesto_obj.ejercicio_id.id
            else:
                record.presupuesto_id = False
                record.ejercicio_id = False

    presupuesto_id = fields.Many2one(
        "crossovered.budget",
        string="Presupuesto",
        compute="_presupuesto_compute",
        store=True,
    )
    ejercicio_id = fields.Many2one(
        "account.fiscalyear",
        string="Ejercicio Fiscal",
        compute="_presupuesto_compute",
        store=True,
    )

    @api.onchange("tipo_beneficiario")
    def _onchange_tipo_beneficiario(self):
        if not self.tipo_beneficiario:
            return {"domain": {"partner_alternate_id": []}}
        return {
            "domain": {
                "partner_alternate_id": [
                    (
                        "id",
                        "in",
                        self.env["res.partner"]
                        .search(
                            [("beneficiary_type_ids", "in", self.tipo_beneficiario.ids)]
                        )
                        .ids,
                    )
                ]
            }
        }

    @api.onchange("event_general")
    def carga_af_datos(self):
        if (
            self.encabezado_view in ["type2","type5"]
        ):

            empleado = self.env["hr.employee"].search(
                [("user_id", "=", self.solicitante.id),]
            )
            self.partner_id=empleado.id
            self.partner_alternate_id=empleado.address_home_id.id

    @api.one
    @api.depends("picking_id", "partner_id", "event_general","solicitud","compromiso","nota_credito")
    def _eventos_contables(self):
        self.code_justificacion = self.justification_id.code
        self.code_evento = self.event_general.codigo
        if (
            self.encabezado_view in ["type6"]
        ):
            empleado = self.env["hr.employee"].search(
                [("user_id", "=", self.solicitante.id),]
            )
            self.partner_id=empleado.id
            self.partner_alternate_id= self.nota_credito.contribuyente_id.id            
            self.no_nota_credito=self.nota_credito.numero
            self.application_concept = self.nota_credito.referenciareintegro
            tipo_ben = self.env["grp.expense.beneficiary.type.catalog"].search([("key", "=", "C01")])
            self.tipo_beneficiario = tipo_ben.id
            if self.partner_id:
                origen_recursos_obj = self.env[
                    "recaudador.fuentesfinanciamiento"
                ].search([("codigo", "=", "1."),])
                self.depedence_id = self.partner_id.department_id.parent_id.id
                self.depedence_ueg_id = self.partner_id.department_id.id
                self.source_finantial_id = origen_recursos_obj.id
            event = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", self.event_general.id)]
            )
            self.justification_id = event.justification_id.id
            self.type_affectation_id = event.affectation_type.id
            self.specific_cluster = self.event_general.padre.id
            self.general_grouter = self.event_general.padre.parent_id.id
            for x in self.nota_credito.cobrosorigen_ids:
                if x.cobro_id.tipo_nota_credito=="parcial":
                    self.number_doc = x.cobro_id.devolucion_lines.numero_oficio
                    self.amparo_folio = x.cobro_id.devolucion_lines.amparo_folio
                if x.cobro_id.tipo_nota_credito=="total":
                    self.number_doc = x.cobro_id.oficio
                    self.amparo_folio = x.cobro_id.amparo

        if (
            self.encabezado_view in ["type2", "type5","type7"]
        ):
            if self.partner_id:
                origen_recursos_obj = self.env[
                    "recaudador.fuentesfinanciamiento"
                ].search([("codigo", "=", "1."),])
                self.depedence_id = self.partner_id.department_id.parent_id.id
                self.depedence_ueg_id = self.partner_id.department_id.id
                self.source_finantial_id = origen_recursos_obj.id
                if self.encabezado_view=="type2":
                    self.partner_alternate_id=self.partner_id.address_home_id.id

            event = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", self.event_general.id)]
            )
            self.justification_id = event.justification_id.id
            self.type_affectation_id = event.affectation_type.id
            self.specific_cluster = self.event_general.padre.id
            self.general_grouter = self.event_general.padre.parent_id.id

        if self.encabezado_view == "type4":
            self.partner_id=self.compromiso.responsible_employee_id.id
            self.partner_alternate_id=self.compromiso.beneficiary_id.id
            self.depedence_id = self.compromiso.up_dependency_id.id
            self.depedence_ueg_id = self.compromiso.ueg_dependency_id.id
            if self.partner_id:
                origen_recursos_obj = self.env[
                        "recaudador.fuentesfinanciamiento"
                    ].search([("codigo", "=", "1."),])
                self.source_finantial_id = origen_recursos_obj.id
            event = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", self.event_general.id)]
            )
            self.justification_id = event.justification_id.id
            self.type_affectation_id = event.affectation_type.id
            self.specific_cluster = self.event_general.padre.id
            self.general_grouter = self.event_general.padre.parent_id.id
            self.number_doc = self.compromiso.number

        if self.encabezado_view == "type3":
            self.partner_alternate_id = self.solicitud.partner_alternate_id.id

            # estos campos computados salen vacíos referenciando a self.solicitud._campo_,
            # modifico a query porque si están almacenados
            # self.depedence_id = self.solicitud.depedence_id.id
            # self.depedence_ueg_id = self.solicitud.depedence_ueg_id.id
            # self.source_finantial_id = self.solicitud.source_finantial_id.id
            if self.solicitud:
                self.env.cr.execute(
                    """
                        Select depedence_id, depedence_ueg_id, source_finantial_id,partner_id,tipo_beneficiario
                            From expense_payment Where id = %s""",
                    (self.solicitud.id,),
                )
                resultado = self.env.cr.fetchall()
                for record in resultado:
                    self.depedence_id = record[0] or False
                    self.depedence_ueg_id = record[1] or False
                    self.source_finantial_id = record[2] or False
                    self.tipo_beneficiario = record[4] or False
                    self.partner_id = record[3] or False

            event = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", self.event_general.id)]
            )
            self.justification_id = event.justification_id.id
            self.type_affectation_id = event.affectation_type.id
            self.application_concept = self.justification_id.name
            self.specific_cluster = self.event_general.padre.id
            self.general_grouter = self.event_general.padre.parent_id.id

            for x in self.beneficiary_ids_FF:
                self.account_payment_id = x.account_payment_id

            if self.encabezado_view == "type3":
                if self.solicitud.suma_total_AF:
                    self.importe_sp_FF = self.solicitud.suma_total_AF
                    if self.solicitud.id:
                        self.env.cr.execute(
                        """
                            Select SUM(t1.total) From expense_payment_detail t1
                            JOIN expense_payment t2 ON t2.id=t1.payment_ff_id WHERE solicitud= %s""",
                        (self.solicitud.id,),
                        )
                        resultado = self.env.cr.fetchall()
                        for record in resultado:
                            self.total_comprobado = record[0] or False

                    self.total_faltante=self.importe_sp_FF-self.total_comprobado
                    self.importe_sp = self.total_faltante
                else:
                    self.importe_sp_FF = self.solicitud.suma_total_PD
                    if self.solicitud.id:
                        self.env.cr.execute(
                        """
                            Select SUM(t1.total) From expense_payment_detail t1
                            JOIN expense_payment t2 ON t2.id=t1.payment_ff_id WHERE solicitud = %s""",
                        (self.solicitud.id,),
                        )
                        resultado = self.env.cr.fetchall()
                        for record in resultado:
                            self.total_comprobado = record[0] or False

                    self.total_faltante=self.importe_sp_FF-self.total_comprobado
                    self.importe_sp = self.total_faltante
        if (
            self.encabezado_view not in ["type2", "type3", "type4", "type5","type6","type7"]
        ):
            event = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", self.event_general.id)]
            )
            self.justification_id = event.justification_id.id
            self.type_affectation_id = event.affectation_type.id
            self.specific_cluster = self.event_general.padre.id
            self.general_grouter = self.event_general.padre.parent_id.id
            if self.po_id:
                self.depedence_id = self.po_id.department_id.id
                self.depedence_ueg_id = self.po_id.dependencia.id
            if self.picking_id:
                self.unit_responsible = self.picking_id.unit_responsable
                self.source_finantial_id = self.picking_id.origin_source.id
                empleado = self.env["hr.employee"].search(
                [("user_id", "=", self.solicitante.id),]
                )
                self.partner_id=empleado.id
                self.partner_alternate_id = self.picking_id.partner_id.id                

        if self.encabezado_view == "type1":
            self.total_pivot = sum([line.price_subtotal for line in self.po_id.order_line])
        if self.encabezado_view == "type2":
            self.total_pivot = self.suma_total_AF
        if self.encabezado_view == "type5":
            self.total_pivot = self.suma_total_PD
        if (self.encabezado_view in ["type3" ,"type4"]):
            self.total_pivot = self.total_ff

    @api.one
    def _compute_total(self):
        if self.encabezado_view == "type1":
            self.total = sum([line.price_subtotal for line in self.po_id.order_line])
        if self.encabezado_view == "type2":
            self.total = self.suma_total_AF
        if self.encabezado_view == "type5":
            self.total = self.suma_total_PD
        if (self.encabezado_view in ["type3" ,"type4"]):
            self.total = self.total_ff

    def _suma_detalle(self):
        reintegro = 0.0
        for x in self:
            event = x.env["grp_account.account.event"].search(
                [("general_event_id", "=", x.event_general.id)]
            )
            for y in x.detail_ids_FF:
                if y.recibo:
                    reintegro += y.total

            if x.detail_ids_FF:
                x.suma_line_FF = sum([line.subtotal for line in x.detail_ids_FF])
                x.impuestos_ff = sum([line.impuestos for line in x.detail_ids_FF])
                x.reintegro = reintegro
                x.total_ff = x.suma_line_FF + x.impuestos_ff
                x.saldo = x.importe_sp - x.total_ff


    @api.multi
    def action_to_authorize(self):
        # CANCELA PRECOMPROMETIDO---------------------------------------------
        if self.solicitud.event_general.precomprometido:
            if self.solicitud.detail_ids:
                for line in self.solicitud.detail_ids:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.solicitud.detail_ids_AF:
                for line in self.solicitud.detail_ids_AF:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.solicitud.detail_ids_PD:
                for line in self.solicitud.detail_ids_PD:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.solicitud.detail_ids_FF:
                for line in self.solicitud.detail_ids_FF:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
        # -------------------------------------------------------
        if self.detail_ids_FF:
            for record in self.detail_ids_FF:
                if record.importe_virtual_disponible<=0.0 and record.comprobacion_factura:
                    raise ValidationError("No se cuenta con presupuesto disponible")
        self.name = self.env["ir.sequence"].next_by_code("expense.payment")

        if self.picking_id:
            self.detail_ids.unlink()
            for item in self.picking_id.move_lines:
                self.env["expense.payment.detail"].create(
                    {
                        "code_item": item.product_id.default_code,
                        "name": item.name,
                        "comprobacion_factura":self.picking_id.digital_invoice.id,
                        "payment_id": self.id,
                        "product_id": item.product_id.id,
                        # "partidas_id": item.partidas_id.id,
                        "estructura_contable_ids": item.key_id.id,
                        "name": item.name,
                        "cantidad_recibida": item.product_uom_qty,
                        "price_unit": item.price_unit,
                         "supplier_taxes_id": [
                            (4, tax.id, 0) for tax in item.product_id.supplier_taxes_id
                        ],
                        "total": item.price_total,
                        "date": self.picking_id.date_order,
                        "number_doc": self.picking_id.digital_invoice.reference,
                    }
                )
        if self.nota_credito:
            self.detail_ids_di.unlink()
            for item in self.nota_credito.items_ids:
                self.env["expense.payment.detail"].create(
                    {
                        "date": self.nota_credito.fecha,
                        "number_doc": self.nota_credito.numero,
                        "name": item.name,
                        "payment_di_id": self.id,
                        "cuenta_contable_di":self.nota_credito.ctacontable_id.id,
                        "total_af": item.subtotal,
                    }
                )
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "to_authorize"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_open_wizard(self, context):
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.states.payment",
            "view_mode": "form",
            "view_type": "form",
            "view_id": self.env.ref(
                "grp_expense.view_state_payment_form"
            ).id,
            "context": context,
            "target": "new"
        }

    @api.multi
    def create_linea_datos_bancarios(self, partner_bank):
        values = {}
        values = {
            "beneficiary_id": self.partner_id.id,
            "payment_id": self.id,
            "beneficiary_type_id": self.partner_alternate_id.beneficiary_type_id.id,
            "beneficiary_alternate_id": self.partner_alternate_id.id,
            "partner_bank": partner_bank,
        }
        self.env["expense.payment.beneficiary"].create(values)

    @api.multi
    def action_first_authorization(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "first_authorization"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_observed(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "observed"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_second_authorization(self):
        # PRECOMPROMETIDO---------------------------------------------
        if self.event_general.precomprometido:
            if self.detail_ids:
                for line in self.detail_ids:
                    line.estructura_contable_ids.precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.id,
                    **{
                        "expense_payment_id": self.id
                    }
                )
            if self.detail_ids_AF:
                for line in self.detail_ids_AF:
                    line.estructura_contable_ids.precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.id,
                    **{
                        "expense_payment_id": self.id
                    }
                )
            if self.detail_ids_PD:
                for line in self.detail_ids_PD:
                    line.estructura_contable_ids.precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.id,
                    **{
                        "expense_payment_id": self.id
                    }
                )
            if self.detail_ids_FF:
                for line in self.detail_ids_FF:
                    line.estructura_contable_ids.precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.id,
                    **{
                        "expense_payment_id": self.id
                    }
                )
        # -------------------------------------------------------
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "second_authorization"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_received(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "received"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_in_review(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "in_review"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_revised(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "revised"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_revised2(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "in_review2"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_validated(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "validated"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_authorized(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "authorized"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_rejected(self):
        # CANCELA PRECOMPROMETIDO---------------------------------------------
        if self.event_general.precomprometido:
            if self.detail_ids:
                for line in self.detail_ids:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.detail_ids_AF:
                for line in self.detail_ids_AF:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.detail_ids_PD:
                for line in self.detail_ids_PD:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total_af,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
            if self.detail_ids_FF:
                for line in self.detail_ids_FF:
                    line.estructura_contable_ids.cancela_precomprometido(
                    line.total,
                    line.date,
                    model_id=self.env['ir.model'].search([('model', '=', 'expense.payment')], limit=1).id,
                    res_id=self.solicitud.id,
                    **{
                        "expense_payment_id": self.solicitud.id
                    }
                )
        # -------------------------------------------------------
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "rejected"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_shipping_box(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "shipping_box"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_draft(self):
        self.state = "draft"
        binnacle_id = self.env["binnacle.state.payment"].create(
            {
                "state": dict(self._fields["state"].selection).get(self.state),
                "expense_id": self.id,
            }
        )
        return self.action_open_wizard(binnacle_id)

    @api.multi
    def action_box(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "entregado_caja"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_scheduled(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "scheduled"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_frozen(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "frozen"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_printed(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "printed"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_sent(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "sent"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_paid(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "paid"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_sent_support(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "env_sop"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)

    @api.multi
    def action_sent_invoice(self):
        context = dict()

        context["state_from"] = self.state
        context["state_to"] = "env_cont"
        context["expense_id"] = self.id

        return self.action_open_wizard(context)


    @api.multi
    def generate_pagos_masivos(self, solicitudes):
        context = dict()
        datos = []
        for x in solicitudes:
            datos.append(x.id)

        context["active_ids"] = list(set(datos))
        action = {
            "name": _("Pagos Masivos"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "expense.pagos",
            "view_id": self.env.ref("grp_expense.view_programacion_pagos").id,
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new",
        }
        return action

    @api.multi
    def recepcion_pagos_masivos(self,solicitudes):
        context = dict()
        datos = []
        for x in solicitudes:
            datos.append(x.id)

        context['active_ids'] = list(set(datos))
        action = {
            'name': _('Pagos'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'expense.pagos.recepcion',
            'view_id': self.env.ref('grp_expense.view_recepcion_pagos').id,
            'type': 'ir.actions.act_window',
            'context':context,
            'target': 'new'
        }
        return action

    @api.multi
    def reporte_solicitudes(self,solicitudes):
        context = dict()
        datos = []
        for x in solicitudes:
            datos.append(x.id)

        context['active_ids'] = list(set(datos))
        action = {
            'name': _('Reporte'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'expense.reportes.solicitud',
            'view_id': self.env.ref('grp_expense.view_report_solicitud').id,
            'type': 'ir.actions.act_window',
            'context':context,
            'target': 'new'
        }
        return action
    
    total_numero = fields.Float(string="Total", readonly=True, compute="_compute_number_total")
    total_letra = fields.Char(string="Total letra", readonly=True, compute="_compute_letters")
    
    @api.depends("detail_ids","detail_ids_FF","detail_ids_di","detail_ids_PD","detail_ids_AF")
    def _compute_number_total(self):
        if self.detail_ids:
            self.total_numero = sum([line.total for line in self.detail_ids])
        elif self.detail_ids_FF:
            self.total_numero = sum([line.total for line in self.detail_ids_FF])
        elif self.detail_ids_di:
            self.total_numero = sum([line.total_af for line in self.detail_ids_di])
        elif self.detail_ids_PD:
            self.total_numero = sum([line.total_af for line in self.detail_ids_PD])
        elif self.detail_ids_AF:
            self.total_numero = sum([line.total_af for line in self.detail_ids_AF])
    
    @api.one
    @api.depends("total_numero")
    def _compute_letters(self):
        self.total_letra = self.numero_a_letras(self.total_numero)
    
    MONEDA_SINGULAR = "peso"
    MONEDA_PLURAL = "pesos"

    CENTIMOS_SINGULAR = "centavo"
    CENTIMOS_PLURAL = "centavos"

    MAX_NUMERO = 999999999999

    UNIDADES = (
        "cero",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco",
        "seis",
        "siete",
        "ocho",
        "nueve",
    )

    DECENAS = (
        "diez",
        "once",
        "doce",
        "trece",
        "catorce",
        "quince",
        "dieciseis",
        "diecisiete",
        "dieciocho",
        "diecinueve",
    )

    DIEZ_DIEZ = (
        "cero",
        "diez",
        "veinte",
        "treinta",
        "cuarenta",
        "cincuenta",
        "sesenta",
        "setenta",
        "ochenta",
        "noventa",
    )

    CIENTOS = (
        "_",
        "ciento",
        "doscientos",
        "trescientos",
        "cuatroscientos",
        "quinientos",
        "seiscientos",
        "setecientos",
        "ochocientos",
        "novecientos",
    )
    
    @api.multi
    def numero_a_letras(self, numero):
        numero_entero = int(numero)
        if numero_entero > self.MAX_NUMERO:
            raise OverflowError(u"Número demasiado alto")
        if numero_entero < 0:
            return "menos %s" % self.numero_a_letras(abs(numero))
        letras_decimal = ""
        parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
        if parte_decimal > 9:
            letras_decimal = "punto %s" % self.numero_a_letras(parte_decimal)
        elif parte_decimal > 0:
            letras_decimal = "punto cero %s" % self.numero_a_letras(parte_decimal)
        if numero_entero <= 99:
            resultado = self.leer_decenas(numero_entero)
        elif numero_entero <= 999:
            resultado = self.leer_centenas(numero_entero)
        elif numero_entero <= 999999:
            resultado = self.leer_miles(numero_entero)
        elif numero_entero <= 999999999:
            resultado = self.leer_millones(numero_entero)
        else:
            resultado = self.leer_millardos(numero_entero)
        resultado = resultado.replace("uno mil", "un mil")
        resultado = resultado.strip()
        resultado = resultado.replace(" _ ", " ")
        resultado = resultado.replace("  ", " ")
        resultado = "%s Pesos %s/100 M.N." % (resultado.capitalize(), parte_decimal)
        return resultado

    @api.multi
    def numero_a_moneda(self, numero):
        numero_entero = int(numero)
        parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
        centimos = ""
        if parte_decimal == 1:
            centimos = self.CENTIMOS_SINGULAR
        else:
            centimos = self.CENTIMOS_PLURAL
        moneda = ""
        if numero_entero == 1:
            moneda = self.MONEDA_SINGULAR
        else:
            moneda = self.MONEDA_PLURAL
        letras = self.numero_a_letras(numero_entero)
        letras = letras.replace("uno", "un")
        letras_decimal = "con %s %s" % (
            self.numero_a_letras(parte_decimal).replace("uno", "un"),
            centimos,
        )
        letras = "%s %s %s" % (letras, moneda, letras_decimal)
        return letras

    @api.multi
    def leer_decenas(self, numero):
        if numero < 10:
            return self.UNIDADES[numero]
        decena, unidad = divmod(numero, 10)
        if numero <= 19:
            resultado = self.DECENAS[unidad]
        elif numero <= 29:
            resultado = "veinti%s" % self.UNIDADES[unidad]
        else:
            resultado = self.DIEZ_DIEZ[decena]
            if unidad > 0:
                resultado = "%s y %s" % (resultado, self.UNIDADES[unidad])
        return resultado

    @api.multi
    def leer_centenas(self, numero):
        centena, decena = divmod(numero, 100)
        if numero == 0:
            resultado = "cien"
        else:
            resultado = self.CIENTOS[centena]
            if decena > 0:
                resultado = "%s %s" % (resultado, self.leer_decenas(decena))
        return resultado

    @api.multi
    def leer_miles(self, numero):
        millar, centena = divmod(numero, 1000)
        resultado = ""
        if millar == 1:
            resultado = ""
        if (millar >= 2) and (millar <= 9):
            resultado = self.UNIDADES[millar]
        elif (millar >= 10) and (millar <= 99):
            resultado = self.leer_decenas(millar)
        elif (millar >= 100) and (millar <= 999):
            resultado = self.leer_centenas(millar)
        resultado = "%s mil" % resultado
        if centena > 0:
            resultado = "%s %s" % (resultado, self.leer_centenas(centena))
        return resultado

    @api.multi
    def leer_millones(self, numero):
        millon, millar = divmod(numero, 1000000)
        resultado = ""
        if millon == 1:
            resultado = " un millon "
        if (millon >= 2) and (millon <= 9):
            resultado = self.UNIDADES[millon]
        elif (millon >= 10) and (millon <= 99):
            resultado = self.leer_decenas(millon)
        elif (millon >= 100) and (millon <= 999):
            resultado = self.leer_centenas(millon)
        if millon > 1:
            resultado = "%s millones" % resultado
        if (millar > 0) and (millar <= 999):
            resultado = "%s %s" % (resultado, self.leer_centenas(millar))
        elif (millar >= 1000) and (millar <= 999999):
            resultado = "%s %s" % (resultado, self.leer_miles(millar))
        return resultado

    @api.multi
    def leer_millardos(self, numero):
        millardo, millon = divmod(numero, 1000000)
        return "%s millones %s" % (self.leer_miles(millardo), self.leer_millones(millon))


class ExpensePaymentDetail(models.Model):
    _name = "expense.payment.detail"

    invoice = fields.Boolean(string="Factura")
    date = fields.Date(string="Fecha")
    number_doc = fields.Char(string="No. Doc.",)
    code_item = fields.Char(string="Cód. Producto")
    name = fields.Char(string="Descripción",)
    state_invoice = fields.Selection(
        [("invoice", "Con factura"), ("not_invoice", "Sin Factura"),],
        default="not_invoice",
        string="Estado",
    )
    payment_id = fields.Many2one("expense.payment", string="Pagos")
    payment_af_id = fields.Many2one("expense.payment", string="Pagos")
    payment_di_id = fields.Many2one("expense.payment", string="Pagos")
    payment_pd_id = fields.Many2one("expense.payment", string="Pagos")
    payment_ff_id = fields.Many2one("expense.payment", string="Pagos")
    payment_sp_id = fields.Many2one("expense.payment", string="Pagos")
    razon_social = fields.Char(string="Razón Social")
    partidas_id = fields.Many2one("rubro.partida", string="Partida-Rubro")
    estructura_contable_ids = fields.Many2one(
        "purchase.estructura.contable",
        string="Clave presupuestal",
        domain="[('partidas_id','=',partidas_id),('departamento_id','=',parent.depedence_ueg_id),('fuentefinanciamiento_origen_id','=',parent.source_finantial_id),('ejercicio_id','=',ejercicio_id)]",
    )
    cuenta_contable = fields.Char(string="Cuenta contable")
    evento_especifico = fields.Text(
        string="Evento específico",
        compute="filtro_partida",
        store=True,
    )
    reintegro = fields.Boolean(string="Reintegro")
    comprobacion_factura = fields.Many2one("account.invoice", string="Factura",)
    recibo = fields.Many2one(
        "cb.order", string="Recibo", domain="[('des_cobro','=','Diversos')]"
    )
    cantidad_recibida = fields.Float(string="Cantidad")
    code_justificacion = fields.Char(
        string="Codigo justificación",
        related="payment_id.code_justificacion",
        default=lambda self: self.env.context.get("code_justificacion", False),
    )
    product_id = fields.Many2one("product.product", string="Producto/Servicio")
    unidad_medida_id = fields.Many2one(
        "product.uom", string="UM", related="product_id.uom_id"
    )
    supplier_taxes_id = fields.Many2many("account.tax", string="Impuesto/Retención")
    price_unit = fields.Float(string="Precio unitario")
    detalle = fields.Char(string="Detalle")
    justificacion_gasto = fields.Char(string="Justificación del gasto")
    details_view_oc = fields.Selection(related="payment_id.event_general.details_view",default="type1",)
    details_view_pd = fields.Selection(related="payment_pd_id.event_general.details_view",default="type3",)
    details_view_ff = fields.Selection(related="payment_ff_id.event_general.details_view",default="type4",)
    recibot=fields.Boolean("recibo")
    cuenta_contable_di = fields.Many2one("account.account",string="Cuenta contable")

    @api.multi
    @api.depends("date")
    def _presupuesto_compute(self):
        for record in self:
            presupuesto_obj = self.env["crossovered.budget"].search(
                [
                    ("state", "=", "done"),
                    ("plantipo", "=", "E"),
                    ("date_from", "<=", record.date),
                    ("date_to", ">=", record.date),
                ]
            )
            if presupuesto_obj:
                record.presupuesto_id = presupuesto_obj.id
                record.ejercicio_id = presupuesto_obj.ejercicio_id.id
            else:
                record.presupuesto_id = False
                record.ejercicio_id = False

    presupuesto_id = fields.Many2one(
        "crossovered.budget",
        string="Presupuesto",
        compute="_presupuesto_compute",
        store=True,
    )
    ejercicio_id = fields.Many2one(
        "account.fiscalyear",
        string="Ejercicio Fiscal",
        compute="_presupuesto_compute",
        store=True,
    )

    @api.depends("price_unit", "cantidad_recibida")
    def _compute_subtotal_total(self):
        for record in self:
            currency = None
            price = record.price_unit
            taxes = []
            if record.supplier_taxes_id:
                taxes = record.supplier_taxes_id.compute_all(
                    price, currency, record.cantidad_recibida, product=record.product_id
                )
            record.impuestos = (
                sum([tax.get("amount") for tax in taxes.get("taxes")]) if taxes else 0
            )
            record.subtotal = record.cantidad_recibida * record.price_unit
            record.total = record.subtotal + record.impuestos

    subtotal = fields.Float("Subtotal", store=True, compute="_compute_subtotal_total")
    total = fields.Float("Total", store=True, compute="_compute_subtotal_total")
    impuestos = fields.Float(
        string="$ Impuestos", store=True, compute="_compute_subtotal_total"
    )
    total_af = fields.Float("Total")

    @api.onchange("comprobacion_factura","date")
    def facturas_almacen_digital(self):
        return {"domain": {"comprobacion_factura": [("type", "=", "in_invoice"),("l10n_mx_edi_sat_status","=","valid")],}}

    @api.onchange("product_id")
    def datos_producto(self):
        for line in self:
            partida = False
            if line.product_id.nivelpadrecog_id:
                    partida = line.product_id.nivelpadrecog_id.partidas_id

            line.partidas_id = partida
        self.price_unit = self.product_id.standard_price

    @api.onchange("recibo")
    def cargar_recibo(self):
        self.total = self.recibo.amount_total
        self.date = self.recibo.date_order
        self.razon_social = self.recibo.contribuyente_nombre
        for x in self.recibo.lines:
            producto = self.env["product.product"].search(
                [("product_tmpl_id", "=", x.product_template_id.id),]
            )
            self.name = x.descripcion
            self.product_id = producto.id
            self.cantidad_recibida = x.qty
            self.cuenta_contable = x.accounting_account.code
            self.price_unit = x.price_unit
            self.subtotal = x.price_subtotal_incl
            self.recibot=True
            taxes = x.env["account.tax"].search(
                [("amount", "=", "0.0000"), ("type_tax_use", "=", "purchase")]
            )
            self.supplier_taxes_id = taxes.ids

    @api.multi
    @api.onchange("date","partidas_id","evento_especifico")
    @api.depends("date","partidas_id","evento_especifico")
    def filtro_partida(self):
        eventos_contables_array = []
        product_template_array = []
        for record in self:
            if record.payment_ff_id:
                if record.payment_ff_id.event_general and record.payment_ff_id.general_grouter and record.payment_ff_id.specific_cluster:
                    try:
                        record.env.cr.execute(
                            """select partidas_id,t1.id from grp_account_specific_event_catalog t1
                        JOIN grp_account_event_grp_account_specific_event_catalog_rel t3 ON t1.id=t3.grp_account_specific_event_catalog_id
                        JOIN grp_account_account_event t2 ON t2.id=t3.grp_account_account_event_id
                        where t1.partidas_id is not null and t1.budgetary = true and t2.general_event_id="""
                            + str(record.payment_ff_id.event_general.id)
                            + """ and t2.generic_grouper_id="""
                            + str(record.payment_ff_id.general_grouter.id)
                            + """ and t2.specific_grouper_id="""
                            + str(record.payment_ff_id.specific_cluster.id)
                        )
                    except Exception as e:
                        raise ValidationError(
                            "No existe un evento contable"
                        )
                else:
                    raise ValidationError(
                            "Sección Eventos Contables Incompleta"
                        )
            if record.payment_pd_id:
                if record.payment_pd_id.event_general and record.payment_pd_id.general_grouter and record.payment_pd_id.specific_cluster:
                    try:
                        record.env.cr.execute(
                            """select partidas_id,t1.id from grp_account_specific_event_catalog t1
                        JOIN grp_account_event_grp_account_specific_event_catalog_rel t3 ON t1.id=t3.grp_account_specific_event_catalog_id
                        JOIN grp_account_account_event t2 ON t2.id=t3.grp_account_account_event_id
                        where t1.partidas_id is not null and t1.budgetary = true and t2.general_event_id="""
                            + str(record.payment_pd_id.event_general.id)
                            + """ and t2.generic_grouper_id="""
                            + str(record.payment_pd_id.general_grouter.id)
                            + """ and t2.specific_grouper_id="""
                            + str(record.payment_pd_id.specific_cluster.id)
                        )
                    except Exception as e:
                        raise ValidationError(
                            "No existe un evento contable"
                        )
                else:
                    raise ValidationError(
                            "Sección Eventos Contables Incompleta"
                        )
            if record.payment_id:
                if record.payment_id.event_general and record.payment_id.general_grouter and record.payment_id.specific_cluster:
                    try:
                        record.env.cr.execute(
                            """select partidas_id,t1.code from grp_account_specific_event_catalog t1
                        JOIN grp_account_event_grp_account_specific_event_catalog_rel t3 ON t1.id=t3.grp_account_specific_event_catalog_id
                        JOIN grp_account_account_event t2 ON t2.id=t3.grp_account_account_event_id
                        where t1.partidas_id is not null and t1.budgetary = true and t2.general_event_id="""
                            + str(record.payment_id.event_general.id)
                            + """ and t2.generic_grouper_id="""
                            + str(record.payment_id.general_grouter.id)
                            + """ and t2.specific_grouper_id="""
                            + str(record.payment_id.specific_cluster.id)
                        )
                    except Exception as e:
                        raise ValidationError(
                            "No existe un evento contable"
                        )
                else:
                    raise ValidationError(
                            "Sección Eventos Contables Incompleta"
                        )
            if record.payment_ff_id or record.payment_pd_id or record.payment_id:
                eventos_contables = record.env.cr.fetchall()
                partidas_ids = 0
                for x in eventos_contables:
                    partidas_ids = x[0]
                    eventos_contables_array.append(str(x[0]))

            if record.partidas_id.id:
                record.env.cr.execute(
                        """select code from grp_account_specific_event_catalog where partidas_id="""+str(record.partidas_id.id))
                evento = record.env.cr.fetchall()
                for y in evento:
                    record.evento_especifico=y[0]

            record.env.cr.execute(
                                """select t2.id from product_template t1
                                    JOIN product_product t2 ON t1.id=t2.product_tmpl_id where t1.check_articulo = true"""
                            )
            product_template = record.env.cr.fetchall()
            for x in product_template:
                product_template_array.append(str(x[0]))

            return {
                "domain": {
                    "partidas_id": [
                        ("tipopartida", "=", "E"),
                        ("id", "in", eventos_contables_array),
                        ("anio","=",record.ejercicio_id.id)
                    ],
                    "product_id": [
                        ("id", "in",product_template_array)
                    ]
                }
            }

    @api.multi
    @api.depends("partidas_id", "estructura_contable_ids")
    def _compute_importe_presupuesto_disponible(self):
        disponible = 0.0
        for record in self:
            if record.estructura_contable_ids:
                disponible = (
                    record.estructura_contable_ids._presupuesto_disponible_anual()
                )
            record.importe_presupuesto_disponible = disponible
            record.importe_virtual_disponible = disponible

    importe_virtual_disponible = fields.Float(
        string="Presupuesto Disponible", digits=0, track_visibility="onchange",store=True,
        compute="_compute_importe_presupuesto_disponible"
    )
    importe_presupuesto_disponible = fields.Float(
        string="Presupuesto disponible",
        digits=0,
        track_visibility="onchange",
        store=True,
        compute="_compute_importe_presupuesto_disponible",
    )

    @api.multi
    def action_cargar_xml(self):
        return {
            "name": ("Cargar Facturas"),
            "view_type": "form",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "wizard.load.xml",
            "view_id": self.env.ref("grp_expense.view_load_xml_form").id,
            "target": "new",
            "flags": {"initial_mode": "view"},
        }


class ExpensePaymentDocuments(models.Model):
    _name = "expense.payment.documents"

    date = fields.Date(string="Fecha", default=fields.Date.today,)
    attachment_id = fields.Many2many("ir.attachment", string="Nombre del documento")
    user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user
    )
    payment_id = fields.Many2one("expense.payment", string="Pagos", ondelete="cascade",)


class ExpensePaymentBeneficiary(models.Model):
    _name = "expense.payment.beneficiary"

    beneficiary_type_id = fields.Many2one(
        "grp.expense.beneficiary.type.catalog", string="Tipo Beneficiario",
    )
    beneficiary_id = fields.Many2one("res.partner", string="Responsable")
    beneficiary_alternate_id = fields.Many2one(
        "res.partner", string="Beneficiario", related="payment_id.partner_alternate_id"
    )
    account_payment_id = fields.Many2one("pay.method", string="Forma de Pago")
    code = fields.Char(string="Forma de pago code", compute="_code")
    check_number = fields.Char(string="No. Cheque",)
    recepcion_check = fields.Boolean(string="Recepción de Cheque")
    type_service = fields.Selection(
        [("service", "Pago de Servicio"), ("productive", "Cadenas Productivas"),],
        string="Tipo de Servicio",
    )
    capture_line = fields.Char(string="Línea de Captura")
    bank_id = fields.Many2one(
        "res.bank", string="Banco", related="partner_bank.bank_id",
    )
    bank_account = fields.Char(
        string="Cuenta Bancaria", related="partner_bank.acc_number",
    )
    clabe = fields.Char(string="CLABE", related="partner_bank.clabe",)
    payment_id = fields.Many2one("expense.payment", string="Pagos")
    partner_bank = fields.Many2one(
        "res.partner.bank",
        string="Nombre de la cuenta",
    )


    @api.onchange("payment_id.beneficiary_alternate_id","account_payment_id")
    def filtro_cuentas_beneficiario(self):
        cuentas_array=[]
        if self.beneficiary_alternate_id.id:
            for record in self:
                record.env.cr.execute(
                                    """select id from res_partner_bank where partner_id="""+str(self.beneficiary_alternate_id.id)+""""""
                                )
                cuentas_bancarias = record.env.cr.fetchall()
                for x in cuentas_bancarias:
                    cuentas_array.append(str(x[0]))
        return {
            "domain": {
                "partner_bank": [
                   ('id','in',cuentas_array)
                ],
                "account_payment_id": [
                   ('code','in',('02','03','NA','REF'))
                ]
            }
        }

    @api.onchange("account_payment_id")
    def forma_pago(self):
        if self.code == "02":
            self.partner_bank = ""

    @api.one
    @api.depends("account_payment_id")
    def _code(self):
        self.code = self.account_payment_id.code


class BinnacleStatePayment(models.Model):
    _name = "binnacle.state.payment"

    user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user, readonly=True
    )
    asignado = fields.Many2one("res.users", string="Asignado", readonly=True)
    date = fields.Datetime(
        string="Fecha", readonly=True, default=lambda self: fields.datetime.now()
    )
    observations = fields.Text(string="Observaciones")
    state = fields.Char(string="Estado", readonly=True)
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
            ("create_check", "Crear Cheque"),
            ("frozen", "Congelado"),
            ("printed", "Impreso"),
            ("sent", "Enviado"),
            ("paid", "Pagado"),
            ("env_sop", "Enviado a Soporte del Gasto"),
            ("env_cont", "Enviado a Contabilidad"),
        ],
        copy=False
    )
    expense_id = fields.Many2one(
        "expense.payment", string="Gastos", ondelete="restrict", readonly=True,
    )
    return_id = fields.Many2one(
        "grp.expense.returns.concept", string="Tipo de Devolución",
    )


class PagosMasivos(models.Model):
    _name = "expense.pagos.masivos"
    _inherit = ["mail.thread", "ir.needaction_mixin"]

    name = fields.Char("Folio", required=True, index=True, copy=False, default="New")
    referencia = fields.Char("Referencia", compute="_compute_referencia")
    state = fields.Selection(
        [("draft", "Borrador"), ("pagado", "Pagado"), ("descargado", "Descargado"),],
        track_visibility="onchange",
        default="draft",
    )
    bank_id = fields.Many2one("res.bank", string="Banco")
    bank_account = fields.Char(string="Cuenta Bancaria")
    date = fields.Date(
        string="Fecha", track_visibility="onchange", default=fields.Date.today,
    )
    total = fields.Float(string="Total", compute="_compute_total", readonly=True)
    solicitud_pago_ids = fields.Many2many("expense.payment")
    forma_pago = fields.Char("Forma de Pago")
    payment_date = fields.Date("Payment Date")

    @api.multi
    def _compute_referencia(self):
        for x in self:
            x.referencia = x.name + "/Banco-" + str(x.bank_id.name)

    @api.multi
    def _compute_total(self):
        self.total = sum([line.total for line in self.solicitud_pago_ids])

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("pagos.masivos.soporte") or "/"
            )
        return super(PagosMasivos, self).create(vals)

    def generate_transfer_file(self):
        # generate text bank file to be downloaded and saved in attachments
        bank_name = self.bank_id.name.lower()
        file_content = self._generate_bank_txt(bank=bank_name)
        xls = False if bank_name != 'banco azteca' else True
        file_name = bank_name + "-" + datetime.today().date().strftime('%Y%m%d') + ".txt" \
            if not xls else bank_name + "-" + datetime.today().date().strftime('%Y%m%d') + ".xls"
        if xls:
            xls_content = base64.encodestring(file_content.read())

        attachment_id = self.env['ir.attachment'].create({
            'name': file_name,
            'datas_fname': file_name,
            'datas': base64.encodestring(file_content) if not xls else xls_content,
            'type': 'binary',
            'mimetype': 'text' if not xls else 'binary',
            'description': bank_name + " Transfer file"
        })
        for record in self:
            record.message_post(attachment_ids=[attachment_id.id])
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(attachment_id.id) + "&filename_field=name&field=datas&download=true&name=" + file_name,  # noqa
            'target': 'new'
        }
        return action

    def _generate_scotiabank_content(self, content=None, details=None, today=None):
        today = today.strftime('%Y%m%d')
        header_file = "EEHA5475601000000000000000000000000000\n"
        header_block = "EEHB000000010018927549999999999000\n"
        trail_block = "EETB000001400000001519146080" + ("0" * 342) + "\n"
        trail_file = "EETA000001400000001519146080" + ("0" * 342) + "\n"
        for detail in self.solicitud_pago_ids:
            amount = str(detail.total).replace(".", "").zfill(15)
            service = "03"
            beneficiary_cve = str(detail.partner_alternate_id.id).zfill(20) #TODO or (detail.partner_alternate_id.beneficiary_type_ids.key + '-' + detail.partner_alternate_id.id).zfill(20)
            beneficiary_rfc = detail.partner_alternate_id.vat
            beneficiary_name = detail.partner_alternate_id.name + abs(
                len(detail.partner_alternate_id.name) - 40) * " "
            payment_ref = detail.name[3:].zfill(16)
            bank_account = detail.clabe.zfill(20) or detail.bank_account.zfill(20)
            account_type = "9"
            bank = "044"  # this correspond to the issuing bank and the receiving bank
            description = detail.application_concept + abs(len(detail.application_concept) - 50) * " "
            details += "EEDA0400" + amount + today + service + beneficiary_cve + beneficiary_rfc + \
                beneficiary_name + payment_ref + "0000000000" + bank_account + "00000" + (" " * 40) + \
                account_type + " " + "00000" + bank + bank + "001" + description[:50] + ("0" * 40) + \
                (" " * 25) + (" " * 21) + "\n"
        content = header_file + header_block + details + trail_block + trail_file

        return content

    def _generate_banamex_content(self, content=None, details=None, today=None):
        origin_account = self.bank_account.zfill(20)
        for detail in self.solicitud_pago_ids:
            partner_bank = detail.env['res.partner.bank'].search(
                [('acc_number', '=', detail.bank_account)], limit=1) if detail.bank_account else "0" * 4
            transaction_type = "09"
            origin_account_type = "01"
            bank_office = partner_bank.emisora.zfill(4) if detail.bank_account else partner_bank
            amount = str(detail.total).replace(".", "").zfill(14)
            currency = "001"
            destination_account_type = "40"
            destination_account = detail.bank_account.zfill(20) if detail.bank_account else ("0" * 20)
            description = detail.application_concept + abs(len(detail.application_concept) - 40) * " "
            reference = detail.name[3:].zfill(7)
            beneficiary_name = detail.partner_alternate_id.name + abs(
                len(detail.partner_alternate_id.name) - 55) * " "
            term = "00"
            rfc = detail.partner_alternate_id.vat
            iva = "0" * 12
            bank = detail.bank_id.sat_bank_id.bic.zfill(4) if detail.bank_id else "0".zfill(4)
            application_date = "0" * 6
            application_time = "0" * 4
            details += transaction_type + origin_account_type + bank_office + origin_account + amount + \
                currency + destination_account_type + destination_account + description[:40] + reference + \
                beneficiary_name[:55] + term + rfc + iva + bank + application_date + application_time + "\n"
        content = details

        return content

    def _generate_bancomer_content(self, content=None, details=None, today=None):
        origin_account = self.bank_account.zfill(18)
        for detail in self.solicitud_pago_ids:
            operation_key = "PSC"
            beneficiary_account = detail.bank_account
            currency = "MXP"
            detail_total = detail.total
            formated_detail_total = "{:.2f}".format(detail_total)
            amount = str(formated_detail_total).zfill(16)
            beneficiary_name = detail.partner_alternate_id.name + abs(
                len(detail.partner_alternate_id.name) - 30) * " "
            account_type = "40"
            bank = detail.bank_id.sat_bank_id.bic.zfill(3)
            description = detail.application_concept + abs(len(detail.application_concept) - 30) * " "
            reference = detail.name[3:].zfill(7)
            availability = "H"
            voucher = "0"
            rfc = " " * 18
            iva = "0" * 12 + ".00"
            details += operation_key + beneficiary_account + origin_account + currency + amount + \
                beneficiary_name[:30] + account_type + bank + description[:30] + reference + \
                availability + voucher + rfc + iva
        content = details

        return content

    def _generate_azteca_content(self, content=None, details=None, today=None, bank_name=None):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        row = 0
        for detail in self.solicitud_pago_ids:
            beneficiary_account = "'" + detail.bank_account
            amount = detail.total
            description = detail.application_concept[:30]
            beneficiary_code = "'" + str(detail.partner_alternate_id.id)
            beneficiary_name = detail.partner_alternate_id.name[:30]
            worksheet.write(row, 0, beneficiary_account)
            worksheet.write(row, 1, amount)
            worksheet.write(row, 2, description)
            worksheet.write(row, 3, beneficiary_code)
            worksheet.write(row, 4, beneficiary_name)
            row += 1
        workbook.close()
        output.seek(0)
        content = output
        return content

    def _generate_banorte_content(self, content=None, details=None, today=None, sequence_number=None):
        register_type = "H"
        service_key = "NE"
        partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', self.bank_account)], limit=1)
        station = partner_bank.emisora.zfill(5) if partner_bank and partner_bank.emisora else "00000"
        process_date = today.strftime('%Y%m%d')
        reference = sequence_number.zfill(2) if sequence_number else "00"
        total_sent_registers = str(len(self.solicitud_pago_ids)).zfill(6) or "0" * 6
        total_sent_registers_amount = str(
            sum([value for value in self.solicitud_pago_ids.mapped('total')])).zfill(15)
        total_new_registers = "0" * 6
        total_new_registers_amount = "0" * 15
        total_new_downs = "0" * 6
        total_new_downs_amount = "0" * 15
        total_verificated_accounts = "0" * 6
        action = "0" * 1
        filler = "0" * 77

        header = register_type + service_key + station + process_date + reference + total_sent_registers + \
            total_sent_registers_amount + total_new_registers + total_new_registers_amount + total_new_downs + \
            total_new_downs_amount + total_verificated_accounts + action + filler

        for detail in self.solicitud_pago_ids:
            register_type = "D"
            application_date = datetime.strptime(self.payment_date, '%Y-%m-%d').strftime('%Y%m%d')
            beneficiary_cve = str(detail.partner_alternate_id.id).zfill(10)
            service_reference = " " * 40
            reference_payer = " " * 40
            amount = str(detail.total).replace(".", "").zfill(15)
            bank_number = "072"
            account_type = "01"
            beneficiary_account = detail.bank_account.zfill(18)
            movement_type = "0"
            action = " "
            iva = "0" * 8
            filler = "0" * 18

            details += register_type + application_date + beneficiary_cve + service_reference + reference_payer + \
                amount + bank_number + account_type + beneficiary_account + movement_type + action + iva + \
                filler + '\n'

        content = header + '\n' + details

        return content

    def _generate_bank_txt(self, bank=None):
        content = ""
        details = ""
        today = datetime.today().date()
        if not bank:
            raise ValidationError(_("The payment should have a Bank selected"))
        if bank == 'scotiabank':
            content = self._generate_scotiabank_content(content, details, today)
        if bank == 'banamex':
            content = self._generate_banamex_content(content, details, today)
        if bank == 'bbva bancomer':
            content = self._generate_bancomer_content(content, details, today)
        if bank == 'banorte':
            sequence_id = self.env['ir.sequence'].search([('name', '=', 'SEQ_BANORTE_TRANFERENCE_FILE_TXT')])
            sequence_number = sequence_id.next_by_code('expense.pagos.masivos').split('/')[1]
            if int(sequence_number) > 99:
                raise ValidationError(_("You have reached the maximum number of prints, please try again tomorrow"))
            content = self._generate_banorte_content(content, details, today, sequence_number)
        if bank == 'banco azteca':
            content = self._generate_azteca_content(content, details, today, bank)

        return content

class ExpensePaymentLine(models.Model):
    _name = "expense.payment.line"
    _auto = False

    estructura_contable_id = fields.Many2one(
        comodel_name = "purchase.estructura.contable",
        string = "Clave Presupuestal"
        )
    total = fields.Float(
        string="Importe"
        )
    payment_id = fields.Many2one(
        comodel_name = "expense.payment",
        string = "Solcitud de pago"
    )
    cantidad_recibida = fields.Integer(
        string="Cantidad"
        )
    product_id = fields.Many2one(
        comodel_name = "product.product",
        string="Producto/Servicio"
        )
    price_unit = fields.Float(
        string="Precio unitario"
        )

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'expense_payment_line')
        self._cr.execute("""
            CREATE OR REPLACE VIEW expense_payment_line AS (
                Select detail.id as id,
                        detail.payment_id as payment_id,
                        detail.estructura_contable_ids as estructura_contable_id,
                        detail.total as total,
                        detail.cantidad_recibida as cantidad_recibida,
                        detail.product_id as product_id,
                        detail.price_unit as price_unit
                    From expense_payment_detail detail
                    Where payment_id is not null
                Union all
                Select detail.id as id,
                        detail.payment_pd_id as payment_id,
                        detail.estructura_contable_ids as estructura_contable_id,
                        detail.total as total,
                        detail.cantidad_recibida as cantidad_recibida,
                        detail.product_id as product_id,
                        detail.price_unit as price_unit
                    From expense_payment_detail detail
                    Where payment_pd_id is not null
                Union all
                Select detail.id as id,
                        detail.payment_ff_id as payment_id,
                        detail.estructura_contable_ids as estructura_contable_id,
                        detail.total as total,
                        detail.cantidad_recibida as cantidad_recibida,
                        detail.product_id as product_id,
                        detail.price_unit as price_unit
                    From expense_payment_detail detail
                    Where payment_ff_id is not null
            )
        """)


class ConfiguracionContableExpensePayment(models.Model):
    _inherit = 'expense.payment'

    @api.multi
    def write(self, values):
        for obj in self:
            old_state = obj.state
            new_state = ''
            state_change = False

            if values.get('state', None):
                new_state = values.get('state')
                state_change = old_state != new_state

            super(ConfiguracionContableExpensePayment, self).write(values)

            if state_change:
                workflow_util = self.env['workflow.util.evento.contable']
                configs = workflow_util.get_configuration(
                    obj,
                    old_state,
                    new_state,
                    obj.event_general.padre.parent_id,
                    obj.event_general.padre,
                    obj.event_general,
                    obj.justification_id,
                    obj.ejercicio_id
                    )

                for parametrizacion_poliza_id in configs:
                    workflow_util.action_account_move_create(parametrizacion_poliza_id, obj)

        return True


class NotaCreditoSolicutud(models.Model):
    _inherit = 'nota.credito'

    solicitud=fields.Many2one("expense.payment", string="Solicitud de Pago")

    @api.multi
    def create_devolucion_ingresos(self):
        empleado = self.env["hr.employee"].search(
                [("user_id", "=", self.env.user.id),]
            )
        tipo_ben = self.env["grp.expense.beneficiary.type.catalog"].search([("key", "=", "C01")])
        evento = self.env["model.cont.eventos"].search([("codigo", "=", "20501")])
        event_contable = self.env["grp_account.account.event"].search(
                [("general_event_id", "=", evento.id)]
            )
        origen_recursos_obj = self.env[
                    "recaudador.fuentesfinanciamiento"
                ].search([("codigo", "=", "1."),])

        payment={}
        payment={
            "partner_id": empleado.id,
            "tipo_beneficiario": tipo_ben.id,
            "partner_alternate_id": self.contribuyente_id.id,
            "event_general": evento.id,
            "no_nota_credito": self.id,
            "nota_credito" : self.numero,
            "justification_id" : event_contable.justification_id.id,
            "type_affectation_id": event_contable.affectation_type.id,
            "specific_cluster" :evento.padre.id,
            "general_grouter" : evento.padre.parent_id.id,
            "source_finantial_id" : origen_recursos_obj.id,
            "depedence_id" : empleado.department_id.parent_id.id,
            "depedence_ueg_id" : empleado.department_id.id
        }
        detalle=self.env['expense.payment'].create(payment)
        self.solicitud=detalle.id

class AccountMoveExpensePayment(models.Model):
    _inherit = 'account.move'

    expense_payment_id = fields.Many2one(
        string = 'Solicitud de pago',
        comodel_name = 'expense.payment'
    )


class ConfigracionChequeras(models.Model):
    _name = "expense.conf.chequeras"

    fecha_alta = fields.Date("Fecha Alta", default= lambda self:fields.datetime.now(), required=True)
    banco = fields.Many2one("res.bank", required=True)
    cuenta = fields.Many2one("res.partner.bank", required=True)
    name = fields.Char("Nombre de la Chequera", required=True)
    tipo_cheque = fields.Selection([
        ('1','Cheque Tercero'),
        ('2','Cheque Propio')], string="Tipo de Cheque", required=True)
    avisar_cheques = fields.Integer("Avisar Cheques Disponibles")
    imp_cheque_aut = fields.Boolean("Imprimir cheque en automático")
    imp_ley_no_neg = fields.Boolean("Imprimir leyenda no negociable")
    imp_ley_cheq = fields.Boolean("Imprimir leyenda del cheque")
    imprimir_nonegociable = fields.Char("Leyenda no negociable", default="NO NEGOCIABLE")
    imprimir_leyendacheque = fields.Char("Leyeda de cheque", default="PARA ABONO EN CUENTA DEL BENEFICIARIO")
    encargado_chequera = fields.Many2one("hr.employee", string="Encargado de Chequera", required=True)
    state = fields.Selection([
        ('draft','Borrador'),
        ('authorized','Autorizado'),
        ('actual','Actual')], default="draft", required=True)
    cheques_ids = fields.One2many(comodel_name='expense.chequeras.historico', inverse_name='parent_id', required=True)
    validate_print = fields.Boolean("Validar", related="cuenta.print_check")
    
    @api.constrains("imp_ley_no_neg")
    def leyenda_no_negociable(self):
        if self.imp_ley_no_neg == False:
            self.imprimir_nonegociable = ""
    
    @api.constrains("imp_ley_cheq")
    def leyenda_cheques(self):
        if self.imp_ley_cheq == False:
            self.imprimir_leyendacheque = ""

    @api.constrains('validate_print')
    def verificar_impresion_cheque(self):
        if not self.validate_print:
            raise ValidationError("La cuenta no tiene habilitada la impresión de cheques")

    @api.multi
    def action_autorizar_cheque(self):
        self.state = "authorized"


    @api.multi
    def action_actual_cheque(self):
        self.state = "actual"

class ConfiguracionChequerasHistorico(models.Model):
    _name = 'expense.chequeras.historico'

    nc = fields.Integer("NC",required=True)
    fecha_alta = fields.Date("Fecha Alta", default= lambda self:fields.datetime.now(), required=True)
    numero_actual = fields.Integer("Número Actual")
    num_cheque_inicial = fields.Integer("Número de cheque inicial", required=True)
    num_cheque_final = fields.Integer("Número de cheque final", required=True)
    total_cheques = fields.Integer("Total de cheques", required=True)
    cheques_disponibles = fields.Integer("Cheques disponibles", required=True, compute="_compute_disponibles", readonly=True)
    parent_id = fields.Many2one('expense.conf.chequeras', readonly=True)
    estado_chequera = fields.Selection([
        ('actual','Actual'),
        ('hecho','Hecho')], readonly=True, default='actual')

    @api.one
    def _compute_disponibles(self):
        self.cheques_disponibles = self.total_cheques - self.numero_actual

    @api.constrains('num_cheque_inicial', 'num_cheque_final')
    def validar_num_cheques(self):
        if self.num_cheque_inicial >= self.num_cheque_final:
            raise ValidationError("Número de cheque inicial debe ser menor al número final")

    @api.one
    def action_estado_chequera(self):
        self.estado_chequera = "hecho"

class ImpresionCheques(models.Model):
    _name = 'expense.impresion.cheques'
    
    @api.one
    @api.depends("total")
    def _compute_to_letter(self):
        self.total_letra = self.numero_a_letras(self.total)

    name = fields.Char("Folio", required=True, index=True, copy=False, default="New")
    nombre_chequera = fields.Many2one("expense.conf.chequeras", string="Chequera", compute="_compute_chequera")
    tipo_cheque = fields.Selection("Tipo de Cheque", related="nombre_chequera.tipo_cheque", readonly=True)
    prueba = fields.Many2one("expense.chequeras.historico")
    cheque_actual = fields.Integer("Número de Cheque")
    fecha = fields.Date("Fecha de Emisión del Cheque", default= lambda self:fields.datetime.now(), required=True)
    total_letra = fields.Char("Importe con Letra", readonly=True, compute="_compute_to_letter")
    leyenda_cheque = fields.Char("Leyenda Cheque", compute="_compute_leyenda", readonly=True)
    state = fields.Selection([
        ('draft','Borrador'),
        ('validated','Validado'),
        ('printed','Impreso')], default="draft", required=True, readonly=True)
    solicitud_pago_ids = fields.Many2many('expense.payment')
    total = fields.Float(string="Total", compute="_compute_total", readonly=True)
    cuenta = fields.Many2one('res.partner.bank',string='Nombre de la Cuenta')
    banco = fields.Many2one("res.bank", string="Banco", related="nombre_chequera.banco", readonly=True)
    
    MONEDA_SINGULAR = "peso"
    MONEDA_PLURAL = "pesos"

    CENTIMOS_SINGULAR = "centavo"
    CENTIMOS_PLURAL = "centavos"

    MAX_NUMERO = 999999999999

    UNIDADES = (
        "cero",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco",
        "seis",
        "siete",
        "ocho",
        "nueve",
    )

    DECENAS = (
        "diez",
        "once",
        "doce",
        "trece",
        "catorce",
        "quince",
        "dieciseis",
        "diecisiete",
        "dieciocho",
        "diecinueve",
    )

    DIEZ_DIEZ = (
        "cero",
        "diez",
        "veinte",
        "treinta",
        "cuarenta",
        "cincuenta",
        "sesenta",
        "setenta",
        "ochenta",
        "noventa",
    )

    CIENTOS = (
        "_",
        "ciento",
        "doscientos",
        "trescientos",
        "cuatroscientos",
        "quinientos",
        "seiscientos",
        "setecientos",
        "ochocientos",
        "novecientos",
    )
    
    @api.multi
    def numero_a_letras(self, numero):
        numero_entero = int(numero)
        if numero_entero > self.MAX_NUMERO:
            raise OverflowError(u"Número demasiado alto")
        if numero_entero < 0:
            return "menos %s" % self.numero_a_letras(abs(numero))
        letras_decimal = ""
        parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
        if parte_decimal > 9:
            letras_decimal = "punto %s" % self.numero_a_letras(parte_decimal)
        elif parte_decimal > 0:
            letras_decimal = "punto cero %s" % self.numero_a_letras(parte_decimal)
        if numero_entero <= 99:
            resultado = self.leer_decenas(numero_entero)
        elif numero_entero <= 999:
            resultado = self.leer_centenas(numero_entero)
        elif numero_entero <= 999999:
            resultado = self.leer_miles(numero_entero)
        elif numero_entero <= 999999999:
            resultado = self.leer_millones(numero_entero)
        else:
            resultado = self.leer_millardos(numero_entero)
        resultado = resultado.replace("uno mil", "un mil")
        resultado = resultado.strip()
        resultado = resultado.replace(" _ ", " ")
        resultado = resultado.replace("  ", " ")
        resultado = "%s Pesos %s/100 M.N." % (resultado, parte_decimal)
        return resultado

    @api.multi
    def numero_a_moneda(self, numero):
        numero_entero = int(numero)
        parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
        centimos = ""
        if parte_decimal == 1:
            centimos = self.CENTIMOS_SINGULAR
        else:
            centimos = self.CENTIMOS_PLURAL
        moneda = ""
        if numero_entero == 1:
            moneda = self.MONEDA_SINGULAR
        else:
            moneda = self.MONEDA_PLURAL
        letras = self.numero_a_letras(numero_entero)
        letras = letras.replace("uno", "un")
        letras_decimal = "con %s %s" % (
            self.numero_a_letras(parte_decimal).replace("uno", "un"),
            centimos,
        )
        letras = "%s %s %s" % (letras, moneda, letras_decimal)
        return letras

    @api.multi
    def leer_decenas(self, numero):
        if numero < 10:
            return self.UNIDADES[numero]
        decena, unidad = divmod(numero, 10)
        if numero <= 19:
            resultado = self.DECENAS[unidad]
        elif numero <= 29:
            resultado = "veinti%s" % self.UNIDADES[unidad]
        else:
            resultado = self.DIEZ_DIEZ[decena]
            if unidad > 0:
                resultado = "%s y %s" % (resultado, self.UNIDADES[unidad])
        return resultado

    @api.multi
    def leer_centenas(self, numero):
        centena, decena = divmod(numero, 100)
        if numero == 0:
            resultado = "cien"
        else:
            resultado = self.CIENTOS[centena]
            if decena > 0:
                resultado = "%s %s" % (resultado, self.leer_decenas(decena))
        return resultado

    @api.multi
    def leer_miles(self, numero):
        millar, centena = divmod(numero, 1000)
        resultado = ""
        if millar == 1:
            resultado = ""
        if (millar >= 2) and (millar <= 9):
            resultado = self.UNIDADES[millar]
        elif (millar >= 10) and (millar <= 99):
            resultado = self.leer_decenas(millar)
        elif (millar >= 100) and (millar <= 999):
            resultado = self.leer_centenas(millar)
        resultado = "%s mil" % resultado
        if centena > 0:
            resultado = "%s %s" % (resultado, self.leer_centenas(centena))
        return resultado

    @api.multi
    def leer_millones(self, numero):
        millon, millar = divmod(numero, 1000000)
        resultado = ""
        if millon == 1:
            resultado = " un millon "
        if (millon >= 2) and (millon <= 9):
            resultado = self.UNIDADES[millon]
        elif (millon >= 10) and (millon <= 99):
            resultado = self.leer_decenas(millon)
        elif (millon >= 100) and (millon <= 999):
            resultado = self.leer_centenas(millon)
        if millon > 1:
            resultado = "%s millones" % resultado
        if (millar > 0) and (millar <= 999):
            resultado = "%s %s" % (resultado, self.leer_centenas(millar))
        elif (millar >= 1000) and (millar <= 999999):
            resultado = "%s %s" % (resultado, self.leer_miles(millar))
        return resultado

    @api.multi
    def leer_millardos(self, numero):
        millardo, millon = divmod(numero, 1000000)
        return "%s millones %s" % (self.leer_miles(millardo), self.leer_millones(millon))
    
    @api.one
    def _compute_leyenda(self):
        for i in self:
            if i.nombre_chequera.imp_ley_cheq == False:
                self.leyenda_cheque = i.nombre_chequera.imprimir_nonegociable
            else:
                self.leyenda_cheque = i.nombre_chequera.imprimir_leyendacheque
            
    
    @api.depends("cuenta")
    def _compute_chequera(self):
        for i in self:
            chequera = i.env['expense.conf.chequeras'].search([('cuenta','=',i.cuenta.id)])
            i.nombre_chequera = chequera.id

    @api.one
    def _compute_total(self):
        self.total = sum([line.total for line in self.solicitud_pago_ids])

    #@api.onchange("nombre_chequera","cuenta","fecha")
    #def _get_numero_actual(self):
    #    chequera_template_array = []
    #    for record in self:
    #        if record.nombre_chequera:
    #
    #            record.env.cr.execute(
    #                """ select id, numero_actual from expense_chequeras_historico WHERE estado_chequera='actual' AND parent_id="""+str(record.nombre_chequera.id)+""""""
    #            )
    #            chequera_template = record.env.cr.fetchall()
    #            for i in chequera_template:
    #                chequera_template_array.append(str(i[0]))
    #                record.cheque_actual = i[1]
    #                record.prueba=i[0]
    #    return {
    #        "domain":{
    #            "prueba":[
    #                ("id","in",chequera_template_array)
    #            ]
    #        }
    #    }

    #@api.constrains("prueba")
    #def _incrementar_cheque(self):
        #self.prueba.numero_actual = self.prueba.numero_actual + 1

    @api.multi
    def action_imprimir_cheque(self):
        return self.env["report"].get_action(self, "grp_expense.report_cheque_general")

    @api.multi
    def action_validar_cheque(self):
        chequera_template_array = []
        for record in self:
            if record.nombre_chequera:

                record.env.cr.execute(
                    """ select id, numero_actual from expense_chequeras_historico WHERE estado_chequera='actual' AND parent_id="""+str(record.nombre_chequera.id)+""""""
                )
                chequera_template = record.env.cr.fetchall()
                for i in chequera_template:
                    chequera_template_array.append(str(i[0]))
                    record.cheque_actual = i[1]
                    record.prueba=i[0]

        self.state = 'validated'
        self.prueba.numero_actual = self.prueba.numero_actual + 1

        self.solicitud_pago_ids.avoid_duplicate_check = True
        #for rec in self.solitud_pago_ids:
        #    rec.avoid_duplicate_check = True

        return {
            "domain":{
                "prueba":[
                    ("id","in",chequera_template_array)
                ]
            }
        }

    def action_print_protect_check(self):
        bank = [record.cuenta.bank_id.name for record in self]
        check_state = [record.state for record in self if record.state != 'printed']
        today = datetime.now()
        if len(set(bank)) > 1:
            raise ValidationError(_("All the checks selected should be from one bank"))
        if not bank[0]:
            raise ValidationError(_("The bank is not defined"))
        if check_state:
            raise ValidationError(_("All the checks should be in 'printed' state"))
        bank = bank[0].lower()
        if bank not in ['banorte', 'banamex', 'bbva bancomer', 'scotiabank']:
            raise ValidationError(_("This bank is not implemented yet"))
        if bank == 'banorte':
            sequence_id = self.env['ir.sequence'].search([('name', '=', 'SEQ_BANORTE_TRANS_TXT')])
            sequence_number = sequence_id.next_by_code('expense.impresion.cheques').split('/')[1]
            if int(sequence_number) > 999:
                raise ValidationError(_("You have reach the maximum number of prints, please wait until tomorrow."))
            file_content = self._banorte_protect_check(sequence_number)
            client_number = self[0].cuenta.reference or "00000000"
            file_name = client_number + today.strftime('%Y%m%d') + '001' + '.CHP'
        if bank == 'banamex':
            file_content = self._banamex_protect_check()
            file_name = bank + "-" + today.strftime('%Y%m%d') + ".txt"
        if bank == 'bbva bancomer':
            file_content = self._bancomer_protect_check()
            file_name = bank + "-" + today.strftime('%Y%m%d') + ".txt"
        if bank == 'scotiabank':
            file_content = self._scotiabank_protect_check()
            file_name = bank + "-" + today.strftime('%Y%m%d') + ".txt"

        attachment_id = self.env['ir.attachment'].create({
            'name': file_name,
            'datas_fname': file_name,
            'datas': base64.encodestring(file_content),
            'type': 'binary',
            'mimetype': 'text',
            'description': bank + " Checks Protection file"
        })
        return {
            'file_name': file_name,
            'file_content': file_content,
            'attachment_id': attachment_id.id,
        }

    def _banamex_protect_check(self):
        content = ""
        currency_dict = {'MXN': '002', 'USD': '005'}
        today = datetime.now()
        for record in self:
            transaction_type = '08'
            origin_account_type = '01'
            origin_account_office = record.cuenta.bank_id.branch_ids[0].code.zfill(4) if \
                record.cuenta.bank_id.branch_ids else '0'.zfill(4)
            origin_account = record.cuenta.bank_id.branch_ids[0].num_cuenta.acc_number.zfill(20) if \
                record.cuenta.bank_id.branch_ids else '0'.zfill(20)
            posting_account_type = '00'
            postin_account_office = '0000'
            posting_account = '00000000000000000000'
            amount = str(record.total).replace(',', '').replace('.', '').zfill(14)
            currency = currency_dict.get(record.cuenta.currency2_id.name) if record.cuenta.currency2_id else '000'
            check_status = '01'
            init_number_check = str(record.cheque_actual).zfill(8) if record.cheque_actual else '0'.zfill(8)
            end_number_check = str(record.cheque_actual).zfill(8) if record.cheque_actual else '0'.zfill(8)
            authorization_number = '000000'
            authorization = '000000'
            aplication_date = today.strftime('%d%m%y')
            application_hour = today.strftime('%H%M')

            content += transaction_type + origin_account_type + origin_account_office + origin_account + \
                posting_account_type + postin_account_office + posting_account + amount + currency + \
                check_status + init_number_check + end_number_check + authorization_number + authorization + \
                aplication_date + application_hour + '\n'

        return content

    def _banorte_protect_check(self, sequence_number):
        content = ""
        currency_dict = {'MXN': 'MXP', 'USD': 'USD'}
        today = datetime.now()
        accounts = [record for record in self.mapped('cuenta')]
        # HEADER
        record_type = 'H'
        account_qty = str(len(set(accounts))).zfill(5)
        application_date = today.strftime('%Y%M%d')
        sequence = str(sequence_number)
        checks_protected_qty = str(len(self)).zfill(5)  # TODO: diff from 'desprotegidos'
        checks_protected_amount = str(sum([value for value in self.mapped('total')])).zfill(18)
        checks_unprotected_qty = '00000'
        checks_unprotected_amount = '0'.zfill(18)
        record_qty = str(len(self)).zfill(5)
        record_amount = str(sum([value for value in self.mapped('total')])).replace(',', '').replace(
            '.', '').zfill(18)
        filler = '0'.zfill(106)

        header = record_type + account_qty + application_date + sequence + checks_protected_qty + \
            checks_protected_amount + checks_unprotected_qty + checks_unprotected_amount + record_qty + \
            record_amount + filler + '\n'

        # DETAILS
        for count, record in enumerate(self):
            bank_account_id = record.env['res.partner.bank'].search(
                [('acc_number', '=', record.solicitud_pago_ids[0].bank_account)], limit=1)
            record_type = 'D'
            service_type = '20'
            record_number = str(count + 1).zfill(5)
            operation_code = '60'
            account_number = record.solicitud_pago_ids[0].bank_account.zfill(10) if \
                record.solicitud_pago_ids and record.solicitud_pago_ids[0].bank_account else '0'.zfill(10)
            document_number = str(record.cheque_actual).zfill(7)
            protection_init_date = today.strftime('%Y%M%d')
            protection_end_date = '20991231'
            amount = str(record.total).replace(',', '').replace('.', '').zfill(13)
            office_code = record.solicitud_pago_ids[0].bank_id.branch_ids[0].code.zfill(4) if \
                record.solicitud_pago_ids[0].bank_id.branch_ids else '0'.zfill(4)
            beneficiary_validation = 'N'
            beneficiary_name = record.solicitud_pago_ids[0].partner_alternate_id.name + abs(
                len(record.solicitud_pago_ids[0].partner_alternate_id.name) - 50) * ' '
            currency = currency_dict.get(bank_account_id.currency2_id.name) if bank_account_id.currency2_id else \
                '0'.zfill(3)
            filler = '0'.zfill(78)

            content += record_type + service_type + record_number + operation_code + account_number + \
                document_number + protection_init_date + protection_end_date + amount + office_code + \
                beneficiary_validation + beneficiary_name + currency + filler + '\n'

        return header + content

    def _bancomer_protect_check(self):
        content = ""
        today = datetime.now()
        accounts = [record.cuenta.acc_number for record in self]
        if len(set(accounts)) > 1:
            raise ValidationError(_("Select the records with the same bank accounts"))
        # HEADER
        account_qty = '1'
        account_number = str(accounts[0]).zfill(18)
        check_qty = str(len(accounts)).zfill(6)
        check_amount = str(sum([value.total for value in self])).replace(',', '').replace('.', '').zfill(15)
        application_date = today.strftime('%Y-%m-%d')
        header = account_qty + '/' + account_number + '/' + check_qty + '/' + check_amount + '/' + application_date

        # DETAILS
        for record in self:
            check_number = str(record.cheque_actual).zfill(7)
            action = 'A'
            amount = str(record.total).replace(',', '').replace('.', '').zfill(15)
            content += check_number + '/' + action + '/' + amount + '\n'

        return header + '\n' + content + '\n'

    def _scotiabank_protect_check(self):
        content = ""
        today = datetime.now()
        currency_dict = {'MXN': '1', 'USD': '2'}

        # HEADER
        record_type = 'H'
        info_date = today.strftime('%Y%m%d')
        filler = ' ' * 140
        move_code = '1'

        header = record_type + info_date + filler + move_code

        # DETAILS
        for record in self:
            partner_bank = record.env['res.partner.bank'].search([('acc_number', '=', record.bank_account)], limit=1)
            record_type = 'A'
            account_square = partner_bank.emisora.zfill(3) if partner_bank and partner_bank.emisora else '000'
            currency = currency_dict.get(record.cuenta.currency2_id.name) if record.cuenta.currency2_id else '0'
            account_number = record.cuenta.acc_number[0:10]
            check_number = str(record.cheque_actual).zfill(10)
            amount = str(record.total).zfill(15)
            beneficiary = record.solicitud_pago_ids[0].partner_alternate_id.name[0:60] + abs(
                len(record.solicitud_pago_ids[0].partner_alternate_id.name) - 60) * ' '
            filler = ' ' * 49
            move_code = '3'
            content += record_type + account_square + currency + account_number + check_number + amount + \
                beneficiary + filler + move_code + '\n'

        # TRAILER
        record_type = 'P'
        total_protected = str(len(self)).zfill(9)
        total_protected_checks = str(len(self)).zfill(15)
        total_protected_amount = str(sum([record.total for record in self])).zfill(18)
        total_unprotected = '0'.zfill(9)
        total_unprotected_checks = '0'.zfill(15)
        total_unprotected_amount = '0.00'.zfill(18)
        total_record = str(len(self)).zfill(10)
        total_checks = str(len(self)).zfill(15)
        total_amount = str(sum([record.total for record in self])).zfill(18)
        filler = ' ' * 21
        move_code = '5'

        trailer = record_type + total_protected + total_protected_checks + total_protected_amount + \
            total_unprotected + total_unprotected_checks + total_unprotected_amount + total_record + total_checks + \
            total_amount + filler + move_code

        return header + '\n' + content + '\n' + trailer

class FormatosCheques(models.Model):
    _inherit = 'report.paperformat'

    ischeck = fields.Boolean(string="¿Formato de cheque?")

class TransferenciaCuentas(models.Model):
    _name = 'expense.transferencia.cuentas'

    name = fields.Char("Folio", required=True, index=True, copy=False, default="New")
    fecha_generacion = fields.Date("Fecha de Generación", default= lambda self:fields.datetime.now(), required=True)
    tipo_pago = fields.Selection([
        ('1','Transferencia Interna')
    ],required=True)
    evento_general = fields.Many2one("model.cont.eventos", string="Evento General", required=True)
    cuenta_origen = fields.Many2one("res.partner.bank", required=True, string="Cuenta Bancaria Origen")
    cuenta_destino = fields.Many2one("res.partner.bank", required=True, string="Cuenta Bancaria Destino")
    referencia = fields.Char(string="Referencia", required=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True)
    total = fields.Monetary(string="Total a Transferir", currency_field="currency_id")
    state = fields.Selection([
        ('draft','Borrador'),
        ('authorized','Autorizado'),
        ('conciled','Conciliado'),
        ('cancelled','Cancelado')
    ], default="draft", required=True, readonly=True)

    @api.constrains('cuenta_origen','cuenta_destino')
    def validate_accounts(self):
        if self.cuenta_origen == self.cuenta_destino:
            raise ValidationError("No se puede hacer un traspaso entre la misma cuenta")

    @api.multi
    def authorize_transfer(self):
        self.state = 'authorized'

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("transferencia.cuentas.sequence") or "/"
            )
        return super(TransferenciaCuentas, self).create(vals)
