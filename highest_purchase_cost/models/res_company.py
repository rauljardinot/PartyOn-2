# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cost_method = fields.Selection(
        selection_add=[
            ('highest_purchase', 'Highest Purchase Price'),
        ],
        ondelete={'highest_purchase': 'set default'},
    )
