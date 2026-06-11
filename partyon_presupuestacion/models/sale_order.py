# -*- coding: utf-8 -*-
from odoo import api, fields, models

class sale_order(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order'

    only_estimate_name = fields.Boolean(string='No pasar detalles')
    partyon_sale_line_ids = fields.One2many('partyon.sale.line', 'sale_order_id', string='Lineas de producto')

