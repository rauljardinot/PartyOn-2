
from odoo import fields, models, api
from odoo.exceptions import UserError
import math

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    _description = 'Purchase Order'

    board_number = fields.Integer(string="N. Planchas") # Para el número que viene del wizard.
    total_price_sale = fields.Monetary(string="Total sin IVA", help="Total de la compra (todas las planchas de la linea) sin contar IVA")
    board_format_id = fields.Many2one(comodel_name='board.format', string="Formato Plancha")
    board_format_name = fields.Char(string="Medidas Plancha")
    board_format_conversion = fields.Float(string="Conversion", compute='_compute_board_conversion') # La conversión que llega del tablero.

    # Ahora no nos lo traemos desde el wizard
    @api.depends('board_format_id')
    def _compute_board_conversion(self):
        for record in self:
            if record.board_format_id:
                record.board_format_conversion = record.board_format_id.area_m2
            else:
                record.board_format_conversion = 0

    # Calculamos aquí el precio de compra real por pié cuadrado:
    @api.onchange('product_id', 'total_price_sale', 'product_qty')
    def _onchange_product_total_price(self):
        if self.total_price_sale and self.product_qty:
            self.price_unit = self.total_price_sale / self.product_qty

    @api.onchange('board_number')
    def _onchange_board_number(self):
        for record in self:
            if record.board_format_id and record.board_format_id.name != 'Por area': # Preguntar si se puede hardcodear.:
                record.product_qty = record.board_format_conversion * record.board_number
            # else:
            #     record.product_qty = 0

    # Para que calcule el total de tableros según el area total. Lanza un wizard si no da un número entero.
    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        for record in self:
            if record.board_format_id and record.board_format_id.name != 'Por area': # Preguntar si se puede hardcodear.
                num_boards = record.product_qty / record.board_format_conversion
                if round(num_boards, 4).is_integer():
                    record.board_number = int(round(num_boards))
                else:
                    # Redondeamos a la siguiente unidad y proponemos esa cantidad a rellenar.
                    next_board = math.ceil(num_boards)
                    suggested_area = next_board * record.board_format_conversion
                    record.board_number = num_boards
                    raise UserError('Debe introducir un área de '+ str(suggested_area) +' Para que funcione')
                    ctx = dict(self.env.context, **{
                        'default_purchase_order_id': self.order_id.id,
                        'default_purchase_line_id': self.id,
                        'default_suggested_area': suggested_area,
                        'default_user_input_area': record.board_number,
                    })
                    return {
                        'name': 'Confirme el area',
                        'type': 'ir.actions.act_window',
                        'res_model': 'apply.area.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': ctx
                    }


