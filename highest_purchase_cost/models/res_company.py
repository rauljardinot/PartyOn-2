# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cost_method = fields.Selection(
        selection_add=[
            ('highest_purchase', 'Mayor precio de compra'),
        ],
        ondelete={'highest_purchase': 'set default'},
    )
