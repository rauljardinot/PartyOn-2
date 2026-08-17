# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_machine_cost_cnc = fields.Many2one('product.product',
                                           string="Producto Costo Máquina CNC",
                                           config_parameter = 'partyon_presupuestacion.product_machine_cost_cnc',
                                           required=True)


    product_machine_cost_wire = fields.Many2one('product.product',
                                           string="Producto Costo Máquina Hilo / Laser",
                                           config_parameter = 'partyon_presupuestacion.product_machine_cost_wire',
                                           required=True)

    product_machine_cost_3d = fields.Many2one('product.product',
                                                string="Producto Costo Impresora 3D",
                                                config_parameter='partyon_presupuestacion.product_machine_cost_3d',
                                                required=True)

