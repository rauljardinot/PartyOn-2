# -*- coding: utf-8 -*-

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        highest_purchase_products = self.filtered(
            lambda product: product.cost_method == 'highest_purchase'
        )
        other_products = self - highest_purchase_products

        result = None
        if other_products:
            result = super(ProductProduct, other_products)._update_standard_price(
                extra_value=extra_value,
                extra_quantity=extra_quantity,
            )

        if highest_purchase_products:
            highest_purchase_products._update_highest_purchase_standard_price()

        return result

    def _update_highest_purchase_standard_price(self):
        for product in self:
            highest_price = product._get_highest_purchase_price()
            if highest_price and highest_price > product.standard_price:
                product.sudo().with_context(
                    disable_auto_revaluation=True,
                ).standard_price = highest_price

    def _get_highest_purchase_price(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'done'),
            '|',
            ('is_in', '=', True),
            ('is_dropship', '=', True),
            ('purchase_line_id', '!=', False),
            ('value', '>', 0),
        ])

        highest_price = 0.0
        for move in moves:
            quantity = move._get_valued_qty()
            if self.uom_id.is_zero(quantity):
                continue
            highest_price = max(highest_price, move.value / quantity)
        return highest_price

    def _run_fifo_batch(self, at_date=None, lot=None, location=None):
        highest_purchase_products = self.filtered(
            lambda product: product.cost_method == 'highest_purchase'
        )
        other_products = self - highest_purchase_products

        std_price_by_product_id = {}
        value_by_product_id = {}
        if other_products:
            std_prices, values = super(ProductProduct, other_products)._run_fifo_batch(
                at_date=at_date,
                lot=lot,
                location=location,
            )
            std_price_by_product_id.update(std_prices)
            value_by_product_id.update(values)

        for product in highest_purchase_products:
            quantity = lot.product_qty if lot else product.qty_available
            std_price_by_product_id[product.id] = product.standard_price
            value_by_product_id[product.id] = product.standard_price * quantity

        return std_price_by_product_id, value_by_product_id

    def _run_fifo(self, quantity, lot=None, at_date=None, location=None):
        self.ensure_one()
        if self.cost_method == 'highest_purchase':
            return quantity * self.standard_price
        return super()._run_fifo(
            quantity,
            lot=lot,
            at_date=at_date,
            location=location,
        )
