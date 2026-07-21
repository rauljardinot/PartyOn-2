# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


LINE_TYPES = [
    ('material', 'Material'),
    ('labor', 'Mano de obra'),
    ('external', 'Servicio externo'),
    ('shipping', 'Envío'),
    ('overhead', 'Coste general'),
    ('extra', 'Extra / imprevisto'),
]

CALCULATION_METHODS = [
    ('manual', 'Cantidad manual'),
    ('area', 'Área (m²)'),
    ('volume', 'Volumen (m³)'),
    ('hours', 'Horas'),
]


class PartyonEstimateCostMixin(models.AbstractModel):
    _name = 'partyon.estimate.cost.mixin'
    _description = 'Datos comunes de costes de presupuestación'

    company_id = fields.Many2one('res.company', string='Compañía')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    sequence = fields.Integer(default=10)
    line_type = fields.Selection(
        LINE_TYPES,
        string='Tipo',
        required=True,
        default='material',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto / recurso',
        check_company=True,
    )
    name = fields.Char(string='Descripción', required=True)
    calculation_method = fields.Selection(
        CALCULATION_METHODS,
        string='Cálculo',
        required=True,
        default='manual',
    )
    manual_quantity = fields.Float(
        string='Cantidad manual',
        default=1.0,
        digits='Product Unit of Measure',
    )
    pieces = fields.Float(
        string='Piezas',
        default=1.0,
        digits='Product Unit of Measure',
    )
    width = fields.Float(string='Ancho (cm)')
    height = fields.Float(string='Alto (cm)')
    depth = fields.Float(string='Profundidad (cm)')
    hours = fields.Float(string='Horas')
    waste_percent = fields.Float(
        string='Merma (%)',
        help='Porcentaje adicional de material por recortes, pruebas o desperdicio.',
    )
    quantity = fields.Float(
        string='Cantidad calculada',
        compute='_compute_quantity',
        store=True,
        digits='Product Unit of Measure',
    )
    uom_id = fields.Many2one('uom.uom', string='Unidad de medida')
    cost_unit = fields.Monetary(
        string='Coste unitario',
        required=True,
        currency_field='currency_id',
    )
    cost_subtotal = fields.Monetary(
        string='Coste total',
        compute='_compute_cost_subtotal',
        store=True,
        currency_field='currency_id',
    )

    @api.depends(
        'calculation_method', 'manual_quantity', 'pieces', 'width', 'height',
        'depth', 'hours', 'waste_percent',
    )
    def _compute_quantity(self):
        for line in self:
            factor = 1.0 + (line.waste_percent / 100.0)
            pieces = line.pieces or 0.0
            if line.calculation_method == 'area':
                base_quantity = line.width * line.height / 10_000.0 * pieces
                line.quantity = base_quantity * factor
            elif line.calculation_method == 'volume':
                base_quantity = line.width * line.height * line.depth / 1_000_000.0 * pieces
                line.quantity = base_quantity * factor
            elif line.calculation_method == 'hours':
                line.quantity = line.hours * pieces
            else:
                line.quantity = line.manual_quantity

    @api.depends('quantity', 'cost_unit')
    def _compute_cost_subtotal(self):
        for line in self:
            line.cost_subtotal = line.quantity * line.cost_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.name = line.product_id.display_name
            line.uom_id = line.product_id.uom_id
            line.cost_unit = line.product_id.standard_price

    @api.constrains(
        'calculation_method', 'manual_quantity', 'pieces', 'width', 'height',
        'depth', 'hours', 'waste_percent', 'cost_unit',
    )
    def _check_cost_inputs(self):
        for line in self:
            if line.cost_unit < 0:
                raise ValidationError(_('El coste unitario no puede ser negativo.'))
            if line.waste_percent < 0:
                raise ValidationError(_('La merma no puede ser negativa.'))
            if line.calculation_method == 'manual' and line.manual_quantity <= 0:
                raise ValidationError(_('La cantidad manual debe ser mayor que cero.'))
            if line.calculation_method in ('area', 'volume'):
                if line.width <= 0 or line.height <= 0 or line.pieces <= 0:
                    raise ValidationError(_('Las dimensiones y las piezas deben ser mayores que cero.'))
            if line.calculation_method == 'volume' and line.depth <= 0:
                raise ValidationError(_('La profundidad debe ser mayor que cero.'))
            if line.calculation_method == 'hours' and (line.hours <= 0 or line.pieces <= 0):
                raise ValidationError(_('Las horas y las piezas deben ser mayores que cero.'))


class PartyonEstimateLine(models.Model):
    _name = 'partyon.estimate.line'
    _description = 'Línea de presupuesto interno'
    _inherit = 'partyon.estimate.cost.mixin'
    _order = 'sequence, id'
    _check_company_auto = True

    estimate_id = fields.Many2one(
        'partyon.estimate',
        string='Presupuesto',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='estimate_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related='estimate_id.currency_id',
        store=True,
    )
    sale_unit = fields.Monetary(
        string='Venta unitaria',
        compute='_compute_sale_values',
        currency_field='currency_id',
    )
    sale_subtotal = fields.Monetary(
        string='Venta total',
        compute='_compute_sale_values',
        currency_field='currency_id',
    )
    margin_amount = fields.Monetary(
        string='Beneficio',
        compute='_compute_sale_values',
        currency_field='currency_id',
    )

    @api.depends(
        'quantity', 'cost_subtotal', 'estimate_id.sale_price',
        'estimate_id.subtotal_cost', 'estimate_id.line_ids.cost_subtotal',
    )
    def _compute_sale_values(self):
        for line in self:
            estimate = line.estimate_id
            if not estimate or not estimate.line_ids:
                sale_subtotal = 0.0
            elif estimate.subtotal_cost:
                sale_subtotal = estimate.sale_price * line.cost_subtotal / estimate.subtotal_cost
            else:
                sale_subtotal = estimate.sale_price / len(estimate.line_ids)
            line.sale_subtotal = sale_subtotal
            line.sale_unit = sale_subtotal / line.quantity if line.quantity else 0.0
            line.margin_amount = sale_subtotal - line.cost_subtotal
