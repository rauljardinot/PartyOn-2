# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_cost_method = fields.Selection(
        selection_add=[
            ('highest_purchase', 'Highest Purchase Price'),
        ],
        ondelete={'highest_purchase': 'set default'},
    )
