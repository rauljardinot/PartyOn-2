
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'
    margin_percentage = fields.Float(string='% de Margen', default=10.0)

    def action_apply_margin(self):
        self.ensure_one()
        if self.margin_percentage:
            self.list_price *= 1 + (self.margin_percentage / 100)



