# -*- coding: utf-8 -*-
{
    "name": "GRP Expense",
    "summary": "Manage Government Expenses",
    "category": "Uncategorized",
    "version": "10.0.2.0.0",
    "author": "Systeg,Vauxoo",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "asti_eaccounting_mx_base",
        "grp_budget",
        "compras_municipio",
        "purchase",
        "finanzas",
    ],
    "data": [
        "data/sequence.xml",
        "data/ir_action_server.xml",
        "data/partner_tags.xml",
        "data/beneficiary_type.xml",
        "security/expense_security.xml",
        "views/account_invoice_view.xml",
        "views/res_partner_view.xml",
        "views/expense_support_view.xml",
        "views/grp_expense_settings.xml",
        "views/settings_view.xml",
        "views/view_eventos.xml",
        "views/location_catalogs.xml",
        "views/returns_concept_view.xml",
        "views/digital_warehouse_view.xml",
        "views/assets.xml",
        "wizard/wizard_load.xml",
        "views/payment.xml",
        "views/stock_picking_view.xml",
        "wizard/wizard_binnacle.xml",
        "wizard/wizard_programacion_pagos.xml",
        "wizard/wizard_recepcion_pagos.xml",
        "wizard/wizard_update_partida.xml",
        "wizard/wizard_payment_masivo.xml",
        "wizard/wizard_report_solicitud.xml",
        "security/ir.model.access.csv",
        "security/menus_security_access.xml",
        "report/report_solicitud_pago.xml",
        "report/report_solicitud_action.xml",
        "report/report_envio_caja.xml",
        "report/report_stock_picking.xml",
        "report/report_cheques.xml",
        "report/report_cheques_action.xml",
        "views/res_partner_compras_municipio.xml",
    ],
    "demo": [],
    "qweb": ["static/src/xml/*.xml",],
    "installable": True,
    "auto_install": False,
}