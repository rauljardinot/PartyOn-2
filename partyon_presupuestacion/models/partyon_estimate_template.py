from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PartyonEstimateTemplate(models.Model):
    _name = 'partyon.estimate.template'
    _description = 'Estimate template'
    _check_company_auto = True

    partyon_estimate_lines_ids = fields.One2many(
        'partyon.estimate.line',
        'template_id',
        string='Composición del producto'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
    )
    name = fields.Char(
        string='Nombre'
    )
    description = fields.Char(string='Descripcion')
    tag = fields.Char(string='Tag')

