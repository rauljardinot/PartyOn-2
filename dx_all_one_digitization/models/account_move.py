from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def action_show_digitalize_wizard(self):
        return {
            'name': 'Digitalizar Factura',
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.digitalize',
            'view_mode': 'form',
            'context': {'active_ids': self.ids},
            'view_id': self.env.ref('dx_all_one_digitization.view_invoice_digitalize_form').id,
            'target': 'new',
        }
