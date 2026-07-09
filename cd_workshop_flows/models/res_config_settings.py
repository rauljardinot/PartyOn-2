
from odoo import fields, models, api


class ResConfigSettins(models.TransientModel):
    _inherit = 'res.config.settings'

    calculate_margin_button = fields.Boolean(
        string='Calculate Margin',
        default=True,
        config_parameter='stock.calculate_margin_button',
        required = True
    )


