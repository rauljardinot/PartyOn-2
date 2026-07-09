from odoo import fields, models, api


class EstimateCategory(models.Model):
    _name = 'estimate.category'
    _description = 'Estimate category'

    name = fields.Char(string='Nombre', help="Nombre de la categoría")