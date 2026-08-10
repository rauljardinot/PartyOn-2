# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_machine_cost = fields.Many2one('product.product',
                                           string="Producto Costo máquina",
                                           config_parameter = 'partyon_presupuestacion.product_machine_cost',
                                           required=True)



