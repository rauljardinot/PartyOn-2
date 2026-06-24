
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'
    margin_percentage = fields.Float(string='% de Margen', default=10.0)

