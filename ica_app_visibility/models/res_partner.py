from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    visible_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "ica_partner_app_visibility_rel",
        "partner_id",
        "menu_id",
        string="Visible Apps",
        domain="[('parent_id', '=', False)]",
        help="Apps that this partner can see in the home menu panel.",
    )
