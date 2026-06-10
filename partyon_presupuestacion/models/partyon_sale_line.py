from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PartyonSaleLine(models.Model):
    _name = 'partyon.sale.line'
    _description = 'Linea de presupuesto partyon'

    name = fields.Char(string='Nombre producto')
    product_id = fields.Many2one('product.product',string='Producto')
    price = fields.Monetary(string='Price')
    cost = fields.Monetary(string='Costo')






