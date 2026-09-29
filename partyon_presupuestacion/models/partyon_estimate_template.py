# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PartyonEstimateTemplate(models.Model):
    _name = 'partyon.estimate.template'
    _description = 'Plantilla de presupuesto'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Descripción')
    category_id = fields.Many2one('estimate.category', string='Categoría')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    margin_type = fields.Selection(
        [
            ('percent', 'Porcentaje sobre coste'),
            ('amount', 'Importe fijo'),
            ('manual', 'Precio final manual'),
        ],
        string='Método de precio',
        required=True,
        default='percent',
    )
    margin_value = fields.Float(string='Margen', default=30.0)
    manual_sale_price = fields.Monetary(
        string='Precio final',
        currency_field='currency_id',
    )
    quote_detail_mode = fields.Selection(
        [('summary', 'Una línea resumida'), ('detail', 'Desglose de líneas')],
        string='Presentación al cliente',
        required=True,
        default='summary',
    )
    line_ids = fields.One2many(
        'partyon.estimate.template.line',
        'template_id',
        string='Composición',
        copy=True,
    )


class PartyonEstimateTemplateLine(models.Model):
    _name = 'partyon.estimate.template.line'
    _description = 'Línea de plantilla de presupuesto'
    _inherit = 'partyon.estimate.cost.mixin'
    _order = 'sequence, id'
    _check_company_auto = True

    template_id = fields.Many2one(
        'partyon.estimate.template',
        string='Plantilla',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='template_id.company_id',
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related='template_id.currency_id',
        store=True,
    )
    machine_time_total = fields.Float(string='Tiempo total de maquinaria', default=0.0)
    machine_time_unit_sel = fields.Selection(
        [('minutes', 'Minutos'), ('hours', 'Horas')],
        string='Unidad de tiempo de máquina',
        default='minutes',
    )
    machine_time_per_unit = fields.Float(
        string='Tiempo de máquina por unidad',
        related='product_id.machine_time_per_unit',
    )
    is_machine_cost_line = fields.Boolean(copy=False, readonly=True)
    need_machine_cost = fields.Boolean(string="Necesita producto de coste", related='product_id.need_machine_cost')
    machine_product_type = fields.Selection(
        [
            ('cnc', 'CNC'),
            ('3d', 'Impresora 3d'),
            ('wire', 'Hilo Caliente'),
        ],
        string="Tipo de producto",
        default='cnc'
    )

    # @api.onchange('product_id', 'quantity')
    # def _onchange_machine_time_total(self):
    #     for line in self:
    #         if line.product_id and line.product_id.need_machine_cost:
    #             line.machine_time_total = line.machine_time_per_unit * line.quantity
    #         else:
    #             line.machine_time_total = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            product = self.env['product.product'].browse(values.get('product_id')).exists()
            if not product:
                continue
            calculation_method = self._get_calculation_method_from_uom(product.uom_id)
            if calculation_method != 'manual' and values.get('calculation_method') in (None, 'manual'):
                values['calculation_method'] = calculation_method
            values.setdefault('uom_id', product.uom_id.id)
            values.setdefault('name', product.display_name)
            values.setdefault('cost_unit', product.standard_price)
        return super().create(vals_list)

    def _prepare_estimate_line_values(self):
        self.ensure_one()
        return {
            'sequence': self.sequence,
            'line_type': self.line_type,
            'product_id': self.product_id.id,
            'name': self.name,
            'calculation_method': self.calculation_method,
            'dimension_uom_id': self.dimension_uom_id.id,
            'manual_quantity': self.manual_quantity,
            'pieces': self.pieces,
            'width': self.width,
            'height': self.height,
            'depth': self.depth,
            'hours': self.hours,
            'time_unit_sel': self.time_unit_sel,
            'waste_percent': self.waste_percent,
            'uom_id': self.uom_id.id,
            'cost_unit': self.cost_unit,
            'machine_time_total': self.machine_time_total,
            'machine_time_unit_sel': self.machine_time_unit_sel,
            'is_machine_cost_line': self.is_machine_cost_line,
            'need_machine_cost': self.need_machine_cost,
            'machine_product_type': self.machine_product_type,
        }
