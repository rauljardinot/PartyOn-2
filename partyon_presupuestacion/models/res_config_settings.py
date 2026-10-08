# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    estimate_default_margin_value = fields.Float(
        string='Margen predeterminado (%)',
        default=40.0,
        config_parameter='partyon_presupuestacion.default_margin_value',
        help='Valor inicial del margen para presupuestos nuevos. El método de precio predeterminado sigue siendo porcentaje sobre coste.',
    )
    estimate_default_discount_renting = fields.Float(
        string='Descuento de alquiler predeterminado',
        default=0.7,
        config_parameter='partyon_presupuestacion.default_discount_renting',
    )
    estimate_default_quote_detail_mode = fields.Selection(
        [
            ('summary', 'Una línea resumida'),
            ('detail', 'Desglose de líneas'),
        ],
        string='Presentación predeterminada al cliente',
        default='summary',
        config_parameter='partyon_presupuestacion.default_quote_detail_mode',
    )
    estimate_default_notes_customer = fields.Text(
        string='Condiciones y notas predeterminadas para el cliente',
        default='',
    )

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

    @api.model
    def get_values(self):
        values = super().get_values()
        values['estimate_default_notes_customer'] = self.env['ir.config_parameter'].sudo().get_param(
            'partyon_presupuestacion.default_notes_customer', '',
        ) or ''
        return values

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'partyon_presupuestacion.default_notes_customer',
            self.estimate_default_notes_customer or '',
        )

