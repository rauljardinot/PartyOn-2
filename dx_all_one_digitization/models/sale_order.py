from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    def action_show_digitalize_wizard(self):
        if not self.partner_id:
            self.partner_id = self.env['res.partner'].search([], limit=1)
        return {
            'name': 'Digitalize Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.digitalize',
            'view_mode': 'form',
            'context': {'active_ids': self.ids},
            'view_id': self.env.ref('dx_all_one_digitization.view_sale_digitalize_form').id,
            'target': 'new',
        }

    def action_open_digitalize_wizard_no_record(self):
        """Open digitization wizard from tree view without selecting a record"""
        return {
            'name': 'Digitalize Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.digitalize',
            'view_mode': 'form',
            'context': {},  # No active_ids, wizard will create new sale order
            'view_id': self.env.ref('dx_all_one_digitization.view_sale_digitalize_form').id,
            'target': 'new',
        }
