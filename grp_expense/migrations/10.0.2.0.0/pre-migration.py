# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID, api, _

_logger = logging.getLogger(__name__)


def update_data(cr):
    cr.execute(
        """
    UPDATE expense_payment SET partner_id=1 
    ;"""
    )

def migrate(cr, version):
    if not version:
        return
    update_data(cr)
