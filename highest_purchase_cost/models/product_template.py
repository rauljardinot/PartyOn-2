# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cost_method = fields.Selection(
        selection_add=[
            ('highest_purchase', 'Highest Purchase Price'),
        ],
    )

    def _get_price_diff_account(self):
        price_diff_account = super()._get_price_diff_account()
        if self.cost_method == 'highest_purchase':
            return self.categ_id.property_price_difference_account_id
        return price_diff_account
