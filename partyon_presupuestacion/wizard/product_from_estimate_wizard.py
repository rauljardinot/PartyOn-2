from odoo import fields, models, api
from odoo.exceptions import AccessError, UserError, ValidationError

class ProductFromEstimateWizard(models.TransientModel):
    _name = 'product.from.estimate.wizard'
    _description = 'Create a product from estimate'

    name = fields.Char(string='Nombre del producto', required=True)
    price = fields.Monetary(string='Precio del producto', default=0, help="Si se deja a '0' se toma el total del presupuesto")
    currency_id = fields.Many2one('res.currency', string='Currencia', default=lambda self: self.env.company.currency_id)


    def action_generate_product(self):
        for record in self:

            estimate_id = self.env.context.get('active_id')
            estimate_active = self.env['partyon.estimate'].browse(estimate_id)

            if not estimate_active:
                raise UserError("No se encuentra el registro del presupuesto")

            if record.price > 0.0:
                price_total = record.price
            else:
                price_total = estimate_active.sale_price

            # Líneas que pasan a las notas
            notes = f"LINEAS DEL PRESUPUESTO : {estimate_active.estimate_name}\n"
            if estimate_active.line_ids:
                for line in estimate_active.line_ids:
                    notes += (f"\n Producto: {line.product_id.name} "
                              f"Cantidad: {line.quantity} {line.uom_id.name}, "
                              f"Precio total : {line.cost_subtotal} €")

            self.env['product.product'].create({
                'name': record.name,
                'standard_price': price_total,
                'list_price': price_total,
                'estimate_notes': notes,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'partyon.estimate',
                'res_id': estimate_id,
                'view_mode': 'form',
                'target': 'current',
            }

