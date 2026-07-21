# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partyon_estimate_id = fields.Many2one(
        'partyon.estimate',
        string='Presupuesto interno',
        copy=False,
        readonly=True,
        check_company=True,
    )
