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
    ('area', 'Área'),
    ('volume', 'Volumen'),
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
    dimension_uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de las medidas',
        domain=[('name', 'in', ['cm', 'm'])], # Para limitar las unidades de las dimensiones, lo suyo es en la vista pero no se actualiza
        default=lambda self: self.env.ref('uom.product_uom_cm'),
        help='Unidad utilizada para ancho, largo y profundidad.',
    )
    width = fields.Float(string='Ancho')
    height = fields.Float(string='Largo')
    depth = fields.Float(string='Profundidad')
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
    cost_unit = fields.Float(
        string='Coste unitario',
        required=True,
        min_display_digits='Product Price',
        help='Coste por cada unidad de consumo seleccionada.',
    )
    cost_subtotal = fields.Monetary(
        string='Coste total',
        compute='_compute_cost_subtotal',
        store=True,
        currency_field='currency_id',
    )

    def _get_calculation_reference_uom(self):
        self.ensure_one()
        xml_ids = {
            'area': 'uom.product_uom_square_meter',
            'volume': 'uom.product_uom_cubic_meter',
            'hours': 'uom.product_uom_hour',
        }
        return self.env.ref(xml_ids[self.calculation_method])

    def _get_calculation_method_from_uom(self, uom):
        if not uom:
            return 'manual'
        references = [
            ('area', self.env.ref('uom.product_uom_square_meter')),
            ('volume', self.env.ref('uom.product_uom_cubic_meter')),
            ('hours', self.env.ref('uom.product_uom_hour')),
        ]
        return next(
            (method for method, reference in references if uom._has_common_reference(reference)),
            'manual',
        )

    def _dimensions_in_meters(self):
        self.ensure_one()
        dimension_uom = self.dimension_uom_id or self.env.ref('uom.product_uom_cm')
        meter = self.env.ref('uom.product_uom_meter')
        if not dimension_uom._has_common_reference(meter):
            return 0.0, 0.0, 0.0
        return (
            dimension_uom._compute_quantity(self.width, meter, round=False),
            dimension_uom._compute_quantity(self.height, meter, round=False),
            dimension_uom._compute_quantity(self.depth, meter, round=False),
        )

    @api.depends(
        'calculation_method', 'manual_quantity', 'pieces', 'width', 'height',
        'depth', 'hours', 'waste_percent', 'dimension_uom_id',
        'dimension_uom_id.factor', 'uom_id', 'uom_id.factor',
    )
    def _compute_quantity(self):
        for line in self:
            factor = 1.0 + (line.waste_percent / 100.0)
            pieces = line.pieces or 0.0
            if line.calculation_method == 'area':
                width, height, _depth = line._dimensions_in_meters()
                base_quantity = width * height * pieces * factor
                reference_uom = line._get_calculation_reference_uom()
                line.quantity = (
                    reference_uom._compute_quantity(base_quantity, line.uom_id, round=False)
                    if line.uom_id and reference_uom._has_common_reference(line.uom_id)
                    else base_quantity
                )
            elif line.calculation_method == 'volume':
                width, height, depth = line._dimensions_in_meters()
                base_quantity = width * height * depth * pieces * factor
                reference_uom = line._get_calculation_reference_uom()
                line.quantity = (
                    reference_uom._compute_quantity(base_quantity, line.uom_id, round=False)
                    if line.uom_id and reference_uom._has_common_reference(line.uom_id)
                    else base_quantity
                )
            elif line.calculation_method == 'hours':
                base_quantity = line.hours * pieces
                reference_uom = line._get_calculation_reference_uom()
                line.quantity = (
                    reference_uom._compute_quantity(base_quantity, line.uom_id, round=False)
                    if line.uom_id and reference_uom._has_common_reference(line.uom_id)
                    else base_quantity
                )
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
            line.calculation_method = line._get_calculation_method_from_uom(line.product_id.uom_id)

    @api.onchange('calculation_method')
    def _onchange_calculation_method(self):
        for line in self:
            if line.calculation_method == 'manual':
                if line.product_id:
                    line.uom_id = line.product_id.uom_id
                    line.cost_unit = line.product_id.standard_price
                continue
            reference_uom = line._get_calculation_reference_uom()
            if line.product_id:
                line.uom_id = line.product_id.uom_id
                line.cost_unit = line.product_id.standard_price
            else:
                line.uom_id = reference_uom

    @api.constrains(
        'calculation_method', 'manual_quantity', 'pieces', 'width', 'height',
        'depth', 'hours', 'waste_percent', 'cost_unit', 'dimension_uom_id',
        'uom_id', 'product_id',
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
                meter = self.env.ref('uom.product_uom_meter')
                if not line.dimension_uom_id or not line.dimension_uom_id._has_common_reference(meter):
                    raise ValidationError(_('La unidad de las medidas debe ser una unidad de longitud.'))
            if line.calculation_method == 'volume' and line.depth <= 0:
                raise ValidationError(_('La profundidad debe ser mayor que cero.'))
            if line.calculation_method == 'hours' and (line.hours <= 0 or line.pieces <= 0):
                raise ValidationError(_('Las horas y las piezas deben ser mayores que cero.'))
            if line.calculation_method != 'manual':
                reference_uom = line._get_calculation_reference_uom()
                if not line.uom_id or not reference_uom._has_common_reference(line.uom_id):
                    raise ValidationError(_(
                        'La unidad de consumo no es compatible con el tipo de cálculo seleccionado.'
                    ))
                if line.product_id and line.uom_id != line.product_id.uom_id:
                    raise ValidationError(_(
                        'La unidad de la línea debe ser la unidad configurada en el producto.'
                    ))


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
    available_quantity = fields.Float(
        string='Disponible',
        compute='_compute_stock_quantities',
        digits='Product Unit of Measure',
    )
    remaining_quantity = fields.Float(
        string='Quedaría',
        compute='_compute_stock_quantities',
        digits='Product Unit of Measure',
    )
    shortage_quantity = fields.Float(
        string='Faltante',
        compute='_compute_stock_quantities',
        digits='Product Unit of Measure',
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

    @api.depends('product_id', 'quantity')
    def _compute_stock_quantities(self):
        for line in self:
            available = (
                line.product_id.with_company(line.company_id).qty_available
                if line.product_id and line.product_id.is_storable else 0.0
            )
            line.available_quantity = available
            line.remaining_quantity = max(available - line.quantity, 0.0)
            line.shortage_quantity = max(line.quantity - available, 0.0)

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
