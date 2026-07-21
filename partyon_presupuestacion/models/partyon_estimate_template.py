# -*- coding: utf-8 -*-

from odoo import fields, models


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

    def _prepare_estimate_line_values(self):
        self.ensure_one()
        return {
            'sequence': self.sequence,
            'line_type': self.line_type,
            'product_id': self.product_id.id,
            'name': self.name,
            'calculation_method': self.calculation_method,
            'manual_quantity': self.manual_quantity,
            'pieces': self.pieces,
            'width': self.width,
            'height': self.height,
            'depth': self.depth,
            'hours': self.hours,
            'waste_percent': self.waste_percent,
            'uom_id': self.uom_id.id,
            'cost_unit': self.cost_unit,
        }
