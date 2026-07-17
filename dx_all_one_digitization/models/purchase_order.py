from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_show_digitalize_wizard(self):
        return {
            'name': 'Digitalize Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.digitalize',
            'view_mode': 'form',
            'context': {'active_ids': self.ids},
            'view_id': self.env.ref('dx_all_one_digitization.view_purchase_digitalize_form').id,
            'target': 'new',
        }
