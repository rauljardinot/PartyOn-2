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
        required=False, # TODO: Preguntar. Lo he hecho False ya que si hay lineas del Template no tienen por que pertenecer a un estimate.
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
    quantity = fields.Float(string='Cantidad', default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
    )

    # -------------------------------------------------------------------------
    # DIMENSIONES Y CÁLCULO DE ÁREA
    # -------------------------------------------------------------------------
    width = fields.Float(string='Ancho (cm)')
    height = fields.Float(string='Alto (cm)')
    depth = fields.Float(string='Profundidad (cm)')
    area = fields.Float(
        string='Área (cm²)',
        compute='_compute_area',
        store=True,
    )

    # -------------------------------------------------------------------------
    # MATERIAL: USO PROPORCIONAL
    # -------------------------------------------------------------------------
    material_width = fields.Float(
        string='Ancho del material (cm)',
        help='Ancho total de la plancha o rollo de material.',
    )
    material_height = fields.Float(
        string='Alto del material (cm)',
        help='Alto total de la plancha o rollo de material.',
    )
    material_area = fields.Float(
        string='Área del material (cm²)',
        compute='_compute_material_area',
        store=True,
    )
    material_usage_ratio = fields.Float(
        string='Ratio de uso (%)',
        compute='_compute_material_usage',
        store=True,
        help='Porcentaje del material que se utiliza para esta pieza.',
    )
    waste_percent = fields.Float(
        string='Desperdicio (%)',
        default=0.0,
        help='Porcentaje estimado de desperdicio del material.',
    )

    # -------------------------------------------------------------------------
    # COSTES UNITARIOS
    # -------------------------------------------------------------------------
    cost_material_unit = fields.Monetary(
        string='Coste material (unitario)',
        currency_field='currency_id',
        help='Coste unitario del material por pieza.',
    )
    cost_waste = fields.Monetary(
        string='Coste desperdicio',
        compute='_compute_cost_waste',
        store=True,
        currency_field='currency_id',
    )
    cost_electricity = fields.Monetary(
        string='Coste eléctrico',
        currency_field='currency_id',
    )
    cost_machine = fields.Monetary(
        string='Coste máquina',
        currency_field='currency_id',
    )
    cost_labor_unit = fields.Monetary(
        string='Coste mano de obra (unitario)',
        currency_field='currency_id',
    )
    cost_design_time = fields.Float(
        string='Horas de diseño',
    )
    cost_design_rate = fields.Monetary(
        string='Tarifa diseño (€/h)',
        currency_field='currency_id',
    )
    cost_handling_time = fields.Float(
        string='Horas de manipulación',
    )
    cost_handling_rate = fields.Monetary(
        string='Tarifa manipulación (€/h)',
        currency_field='currency_id',
    )
    cost_painting = fields.Monetary(
        string='Coste pintura / acabado',
        currency_field='currency_id',
    )
    cost_shipping = fields.Monetary(
        string='Coste envío',
        currency_field='currency_id',
    )
    cost_extra = fields.Monetary(
        string='Otros gastos',
        currency_field='currency_id',
    )
    cost_extra_description = fields.Char(
        string='Descripción gastos extra',
    )

    # -------------------------------------------------------------------------
    # SUBTOTALES COMPUTED POR CATEGORÍA
    # -------------------------------------------------------------------------
    subtotal_material = fields.Monetary(
        string='Subtotal material',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
    subtotal_operation = fields.Monetary(
        string='Subtotal operaciones',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
        help='Máquina + electricidad',
    )
    subtotal_labor = fields.Monetary(
        string='Subtotal mano de obra',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
        help='Mano de obra + diseño + manipulación',
    )
    subtotal_overhead = fields.Monetary(
        string='Subtotal generales',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
        help='Pintura/acabado',
    )
    subtotal_shipping = fields.Monetary(
        string='Subtotal envío',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
    subtotal_extra = fields.Monetary(
        string='Subtotal extra',
        compute='_compute_subtotals',
        store=True,
        currency_field='currency_id',
    )
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
    sale_price_unit = fields.Monetary(
        string='Precio venta unitario',
        compute='_compute_sale_price_unit',
        store=True,
        currency_field='currency_id',
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    @api.depends('width', 'height')
    def _compute_area(self):
        for line in self:
            line.area = line.width * line.height

    @api.depends('material_width', 'material_height')
    def _compute_material_area(self):
        for line in self:
            line.material_area = line.material_width * line.material_height

    @api.depends('area', 'material_area')
    def _compute_material_usage(self):
        for line in self:
            if line.material_area:
                line.material_usage_ratio = (line.area / line.material_area) * 100.0
            else:
                line.material_usage_ratio = 0.0

    @api.depends('cost_material_unit', 'waste_percent')
    def _compute_cost_waste(self):
        for line in self:
            line.cost_waste = line.cost_material_unit * (line.waste_percent / 100.0)

    @api.depends(
        'quantity',
        'cost_material_unit', 'cost_waste',
        'cost_electricity', 'cost_machine',
        'cost_labor_unit',
        'cost_design_time', 'cost_design_rate',
        'cost_handling_time', 'cost_handling_rate',
        'cost_painting',
        'cost_shipping',
        'cost_extra',
    )
    def _compute_subtotals(self):
        for line in self:
            qty = line.quantity

            # Material: (coste unitario + desperdicio) × cantidad
            line.subtotal_material = (line.cost_material_unit + line.cost_waste) * qty

            # Operaciones: (máquina + electricidad) × cantidad
            line.subtotal_operation = (line.cost_machine + line.cost_electricity) * qty

            # Mano de obra: labor unitario × qty + diseño + manipulación
            design_cost = line.cost_design_time * line.cost_design_rate
            handling_cost = line.cost_handling_time * line.cost_handling_rate
            line.subtotal_labor = (line.cost_labor_unit * qty) + design_cost + handling_cost

            # Generales: pintura/acabado × cantidad
            line.subtotal_overhead = line.cost_painting * qty

            # Envío
            line.subtotal_shipping = line.cost_shipping

            # Extra
            line.subtotal_extra = line.cost_extra

            # Total línea
            line.line_subtotal = (
                line.subtotal_material
                + line.subtotal_operation
                + line.subtotal_labor
                + line.subtotal_overhead
                + line.subtotal_shipping
                + line.subtotal_extra
            )

    @api.depends(
        'line_subtotal', 'quantity',
        'line_margin_type', 'line_margin_value',
        'estimate_id.margin_type', 'estimate_id.margin_value',
    )
    def _compute_sale_price_unit(self):
        for line in self:
            subtotal = line.line_subtotal
            qty = line.quantity or 1.0

            if line.line_margin_type == 'percent':
                margin_val = line.line_margin_value
                price = subtotal * (1 + margin_val / 100.0)
            elif line.line_margin_type == 'amount':
                price = subtotal + line.line_margin_value
            else:
                # 'global' — usa margen del presupuesto padre
                est = line.estimate_id
                if est.margin_type == 'percent':
                    price = subtotal * (1 + (est.margin_value / 100.0))
                elif est.margin_type == 'amount':
                    # Distribuir proporcionalmente el importe fijo
                    total_cost = est.subtotal_cost or 1.0
                    price = subtotal + (est.margin_value * subtotal / total_cost)
                else:
                    # Manual — distribuir proporcionalmente
                    total_cost = est.subtotal_cost or 1.0
                    if est.manual_sale_price:
                        price = est.manual_sale_price * subtotal / total_cost
                    else:
                        price = subtotal
            line.sale_price_unit = price / qty if qty else price

    # -------------------------------------------------------------------------
    # ONCHANGE
    # -------------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.cost_material_unit = self.product_id.standard_price

