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
    # Precio de Venta Unitario
    # -------------------------------------------------------------------------
    lst_price = fields.Float('Precio de Venta', currency_field='currency_id', help='Precio unitario del material por pieza.')
    # -------------------------------------------------------------------------
    # COSTES UNITARIOS
    # -------------------------------------------------------------------------
    cost_product_unit = fields.Monetary(
        string='Coste/Unitario',
        currency_field='currency_id',
        help='Coste unitario del material por pieza.',
    )
    # Coste unitario real contando el beneficio.
    cost_unit_real = fields.Monetary(
        string='Coste/Unitario',
        currency_field='currency_id',
        # compute='_compute_cost_unit_real',
        help='Coste unitario del material por pieza.',
    )
    # -------------------------------------------------------------------------
    # SUBTOTALES COMPUTED POR CATEGORÍA
    # -------------------------------------------------------------------------

    line_subtotal = fields.Monetary(
        string='Precio Total',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
    line_cost_subtotal = fields.Monetary(
        string='Coste Total',
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
            # qty = line.quantity
            line.line_subtotal = line.lst_price * line.quantity
            line.line_cost_subtotal = line.cost_product_unit * line.quantity

    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            if self.product_id:
                record.name = record.product_id.display_name
                record.uom_id = record.product_id.uom_id
                record.cost_product_unit = record.product_id.standard_price
                record.product_margin_percentage = record.product_id.margin_percentage or 0.0
                record.lst_price = record.product_id.lst_price

                # record.cost_unit_real = record.product_id.standard_price
