# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PartyonEstimateLine(models.Model):
    _name = 'partyon.estimate.line'
    _description = 'Línea de Presupuestación Interna'
    _order = 'sequence, id'

    # -------------------------------------------------------------------------
    # RELACIÓN CON EL PRESUPUESTO
    # -------------------------------------------------------------------------
    estimate_id = fields.Many2one(
        'partyon.estimate',
        string='Presupuesto',
        required=False,
        # TODO: Preguntar. Lo he hecho False ya que si hay lineas del Template no tienen por que pertenecer a un estimate.
        ondelete='cascade',
        index=True,
    )
    # Relación con el Template:
    template_id = fields.Many2one(
        'partyon.estimate.template',
        string='Plantilla',
    )
    company_id = fields.Many2one(
        related='estimate_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        related='estimate_id.currency_id',
        store=True,
    )
    sequence = fields.Integer(string='Secuencia', default=10)

    # -------------------------------------------------------------------------
    # PRODUCTO / MATERIAL
    # -------------------------------------------------------------------------
    product_id = fields.Many2one(
        'product.product',
        string='Material / Producto',
    )
    name = fields.Char(string='Descripción')
    quantity = fields.Float(string='Cantidad', default=1.0, compute='_compute_quantity')
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
    )
    product_margin_percentage = fields.Float(string='Margen Material')

    # -------------------------------------------------------------------------
    # DIMENSIONES Y CÁLCULO DE ÁREA
    # -------------------------------------------------------------------------
    width = fields.Float(string='Ancho (cm)')
    height = fields.Float(string='Alto (cm)')
    depth = fields.Float(string='Profundidad (cm)')  # TODO: Este campo puede valer pero para el corcho blanco solo.
    area = fields.Float(
        string='Área (cm²)',
        compute='_compute_area',
        store=True,
    )
    # -------------------------------------------------------------------------
    # COSTES UNITARIOS
    # -------------------------------------------------------------------------
    cost_product_unit = fields.Monetary(
        string='Coste material (unitario)',
        currency_field='currency_id',
        help='Coste unitario del material por pieza.',
    )
    # Coste unitario real contando el beneficio.
    cost_unit_real = fields.Monetary(
        string='Coste Real Ud.',
        currency_field='currency_id',
        # compute='_compute_cost_unit_real',
        help='Coste unitario del material por pieza.',
    )
    # -------------------------------------------------------------------------
    # SUBTOTALES COMPUTED POR CATEGORÍA
    # -------------------------------------------------------------------------

    line_subtotal = fields.Monetary(
        string='Total línea',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
    # -------------------------------------------------------------------------
    # MARGEN POR LÍNEA
    # -------------------------------------------------------------------------
    line_margin_type = fields.Selection(
        selection=[
            ('global', 'Usar margen global'),
            ('percent', 'Porcentaje'),
            ('amount', 'Importe fijo'),
        ],
        string='Tipo de margen (línea)',
        default='global',
    )
    line_margin_value = fields.Float(
        string='Valor margen (línea)',
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    @api.depends('width', 'height')
    def _compute_area(self):
        for line in self:
            line.area = line.width * line.height

    @api.depends('width', 'height', 'uom_id')
    def _compute_quantity(self):
        for line in self:
            if line.width and line.height:
                if line.uom_id.name == 'm²':
                    line.quantity = (line.width * line.height) / 10000  # Para que nos den los m2
                elif line.uom_id.name == 'cm²':
                    line.quantity = line.width * line.height
                else:
                    line.quantity = 0
            else:
                line.quantity = 0

    @api.depends('material_width', 'material_height')
    def _compute_material_area(self):
        for line in self:
            line.material_area = line.material_width * line.material_height

    """
         TODO: Añadir los extras al precio unitario y después multiplicar por la cantidad. Reformularlo ya que 
         los productos que lleguen a las lineas pueden ser tanto materiales como servicios (horas de trabajo) 
         por lo que la linea ha de calcularlo de forma independiente, aunque puede ser válido el campo para sacar
         métricas y datos a partir de ahi... 
     """

    @api.depends('quantity', 'cost_product_unit')
    def _compute_subtotals(self):
        for line in self:
            qty = line.quantity
            line.line_subtotal = line.cost_unit_real * qty

    # # Coste real por unidad
    # @api.depends('product_id')
    # def _compute_cost_unit_real(self):
    #     for record in self:
    #         if record.product_id:
    #             record.cost_unit_real = record.cost_product_unit * (1 + record.product_margin_percentage / 100)

    # Precio real de la línea con el beneficio.
    # @api.depends(
    #     'line_subtotal', 'quantity',
    #     'line_margin_type', 'line_margin_value',
    #     'estimate_id.margin_type', 'estimate_id.margin_value',
    # )
    # # def _compute_sale_price_unit(self):
    # #     for line in self:
    # #         subtotal = line.line_subtotal
    # #         qty = line.quantity or 1.0
    # #
    # #         if line.line_margin_type == 'percent':
    # #             margin_val = line.line_margin_value
    # #             price = subtotal * (1 + margin_val / 100.0)
    # #         elif line.line_margin_type == 'amount':
    # #             price = subtotal + line.line_margin_value
    # #         else:
    # #             # 'global' — usa margen del presupuesto padre
    # #             est = line.estimate_id
    # #             if est.margin_type == 'percent':
    # #                 price = subtotal * (1 + (est.margin_value / 100.0))
    # #             elif est.margin_type == 'amount':
    # #                 # Distribuir proporcionalmente el importe fijo
    # #                 total_cost = est.subtotal_cost or 1.0
    # #                 price = subtotal + (est.margin_value * subtotal / total_cost)
    # #             else:
    # #                 # Manual — distribuir proporcionalmente
    # #                 total_cost = est.subtotal_cost or 1.0
    # #                 if est.manual_sale_price:
    # #                     price = est.manual_sale_price * subtotal / total_cost
    # #                 else:
    # #                     price = subtotal
    # #         line.sale_price_unit = price / qty if qty else price

    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            if self.product_id:
                record.name = record.product_id.display_name
                record.uom_id = record.product_id.uom_id
                record.cost_product_unit = record.product_id.list_price or 0.0
                record.product_margin_percentage = record.product_id.margin_percentage or 0.0

                record.cost_unit_real = record.cost_product_unit * (1 + record.product_margin_percentage / 100) or 0.0
