# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    need_machine_cost = fields.Boolean(
        string="Incluye Horas de Máquina",
        default=False,
        help="Marcar en el caso de que este producto genere una linea de coste de máquinaria en la presupuestación.",
    )
    machine_time_per_unit = fields.Float(string="Tiempo de maquina por Unidad (horas)")


