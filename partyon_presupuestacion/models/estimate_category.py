from odoo import fields, models


class EstimateCategory(models.Model):
    _name = 'estimate.category'
    _description = 'Categoría de presupuesto'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        'UNIQUE(name)',
        'Ya existe una categoría con este nombre.',
    )
