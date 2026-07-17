from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PartyonSaleLine(models.Model):
    _name = 'partyon.sale.line'
    _description = 'Linea de presupuesto partyon'

    product_id = fields.Many2one(
        'product.product',
        string='Material / Producto',)
    product_name = fields.Char(string='Nombre producto')
    price = fields.Monetary(string='Precio',store=True,currency_field='currency_id',)
    cost = fields.Monetary(string='Costo',store=True,currency_field='currency_id',)
    currency_id = fields.Many2one('res.currency',string='Moneda', default=lambda self: self.env.company.currency_id)
    sale_order_id = fields.Many2one('sale.order',string='Presupuesto')
    unit_price = fields.Monetary(string='Precio unidad')
    product_amount = fields.Integer(string='Cantidad')
    taxes_id = fields.Many2many('account.tax', string='Impuestos')
    line_total = fields.Monetary(string='Total')










