# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class PartyonEstimate(models.Model):
    _name = 'partyon.estimate'
    _description = 'Presupuesto interno PartyOn'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
    )
    estimate_name = fields.Char(string='Trabajo', required=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        check_company=True,
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Oportunidad',
        tracking=True,
        check_company=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
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
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_validity = fields.Date(string='Válido hasta')
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('review', 'En revisión'),
            ('approved', 'Aprobado'),
            ('quoted', 'Cotizado'),
            ('customer_approved', 'Aceptado por cliente'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado',
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )
    version = fields.Integer(string='Versión', default=1, copy=False, readonly=True)
    parent_estimate_id = fields.Many2one(
        'partyon.estimate',
        string='Versión anterior',
        copy=False,
        readonly=True,
    )
    child_estimate_ids = fields.One2many(
        'partyon.estimate',
        'parent_estimate_id',
        string='Versiones posteriores',
    )
    line_ids = fields.One2many(
        'partyon.estimate.line',
        'estimate_id',
        string='Líneas de coste',
        copy=True,
    )
    description = fields.Text(string='Descripción del trabajo')
    notes_internal = fields.Text(string='Notas internas')
    notes_customer = fields.Text(string='Condiciones y notas para el cliente')
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Cotización',
        copy=False,
        readonly=True,
    )
    sale_order_state = fields.Selection(related='sale_order_id.state')
    project_id = fields.Many2one('project.project', string='Proyecto', copy=False)
    template_id = fields.Many2one(
        'partyon.estimate.template',
        string='Plantilla',
        check_company=True,
    )
    estimate_category_id = fields.Many2one('estimate.category', string='Categoría')

    total_material_cost = fields.Monetary(
        string='Materiales', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_labor_cost = fields.Monetary(
        string='Mano de obra', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_external_cost = fields.Monetary(
        string='Servicios externos', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_shipping_cost = fields.Monetary(
        string='Envío', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_overhead_cost = fields.Monetary(
        string='Costes generales', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_extra_cost = fields.Monetary(
        string='Extras / imprevistos', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    subtotal_cost = fields.Monetary(
        string='Coste total', compute='_compute_totals', store=True,
        currency_field='currency_id',
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
        tracking=True,
    )
    margin_value = fields.Float(
        string='Margen',
        default=30.0,
        help='Porcentaje sobre el coste o importe fijo, según el método elegido.',
    )
    manual_sale_price = fields.Monetary(
        string='Precio final manual',
        currency_field='currency_id',
    )
    sale_price = fields.Monetary(
        string='Precio de venta', compute='_compute_sale_price', store=True,
        currency_field='currency_id',
    )
    margin_amount = fields.Monetary(
        string='Beneficio', compute='_compute_sale_price', store=True,
        currency_field='currency_id',
    )
    margin_percent = fields.Float(
        string='Margen sobre coste', compute='_compute_sale_price', store=True,
        help='Beneficio dividido entre el coste total.',
    )
    sale_tax_amount = fields.Monetary(
        string='IVA',
        compute='_compute_sale_tax_totals',
        currency_field='currency_id',
    )
    sale_total = fields.Monetary(
        string='Total con IVA',
        compute='_compute_sale_tax_totals',
        currency_field='currency_id',
    )
    quote_detail_mode = fields.Selection(
        [('summary', 'Una línea resumida'), ('detail', 'Desglose de líneas')],
        string='Presentación al cliente',
        required=True,
        default='summary',
    )
    approved_by = fields.Many2one(
        'res.users', string='Aprobado por', copy=False, readonly=True,
    )
    approved_date = fields.Datetime(
        string='Fecha de aprobación', copy=False, readonly=True,
    )
    is_for_renting = fields.Boolean(string="Para Alquiler", default=False)

    product_ids = fields.One2many('product.product', inverse_name='estimate_id', string='Productos')
    product_count = fields.Integer(string="Productos", compute='_compute_product_count', store=True,)


    @api.depends('product_ids')
    def _compute_product_count(self):
        for record in self:
            if record.product_ids:
                record.product_count = len(record.product_ids)
            else:
                record.product_count = 0

    def action_show_products(self):
        return {
            "name": "Productos",
            "type": "ir.actions.act_window",
            'domain': [('estimate_id', '=', self.id)],
            "view_mode": "list,form",
            'context': {'default_estimate_id': self.id},
            "res_model": "product.product",
            "target": "current",
        }

    @api.depends('line_ids.line_type', 'line_ids.cost_subtotal')
    def _compute_totals(self):
        total_fields = {
            'material': 'total_material_cost',
            'labor': 'total_labor_cost',
            'external': 'total_external_cost',
            'shipping': 'total_shipping_cost',
            'overhead': 'total_overhead_cost',
            'extra': 'total_extra_cost',
        }
        for estimate in self:
            totals = dict.fromkeys(total_fields, 0.0)
            for line in estimate.line_ids:
                totals[line.line_type] += line.cost_subtotal
            for line_type, field_name in total_fields.items():
                estimate[field_name] = totals[line_type]
            estimate.subtotal_cost = sum(totals.values())

    @api.depends('subtotal_cost', 'margin_type', 'margin_value', 'manual_sale_price')
    def _compute_sale_price(self):
        for estimate in self:
            if estimate.margin_type == 'percent':
                sale_price = estimate.subtotal_cost * (1.0 + estimate.margin_value / 100.0)
            elif estimate.margin_type == 'amount':
                sale_price = estimate.subtotal_cost + estimate.margin_value
            else:
                sale_price = estimate.manual_sale_price
            estimate.sale_price = sale_price
            estimate.margin_amount = sale_price - estimate.subtotal_cost
            estimate.margin_percent = (
                estimate.margin_amount / estimate.subtotal_cost
                if estimate.subtotal_cost else 0.0
            )

    @api.depends('line_ids.sale_tax_amount', 'line_ids.sale_total')
    def _compute_sale_tax_totals(self):
        for estimate in self:
            estimate.sale_tax_amount = sum(estimate.line_ids.mapped('sale_tax_amount'))
            estimate.sale_total = sum(estimate.line_ids.mapped('sale_total'))

    def get_tax_summary(self):
        """Desglose del IVA del presupuesto agrupado por impuesto (para el PDF).

        Devuelve una lista de dicts {'name', 'base', 'amount'} ordenada por
        la secuencia de los impuestos.
        """
        self.ensure_one()
        summary = {}
        for line in self.line_ids:
            if not line.tax_ids or not line.sale_subtotal:
                continue
            res = line.tax_ids.compute_all(
                line.sale_subtotal,
                currency=line.currency_id,
                quantity=1.0,
                product=line.product_id,
                partner=self.partner_id,
            )
            for tax_values in res.get('taxes', []):
                entry = summary.setdefault(tax_values['id'], {
                    'name': tax_values['name'],
                    'base': 0.0,
                    'amount': 0.0,
                })
                entry['base'] += tax_values.get('base', 0.0)
                entry['amount'] += tax_values.get('amount', 0.0)
        taxes = self.env['account.tax'].browse(summary.keys())
        taxes = taxes.sorted(key=lambda tax: (tax.sequence, tax.id))
        return [summary[tax.id] for tax in taxes]

    @api.constrains('margin_value', 'manual_sale_price', 'margin_type')
    def _check_margin_values(self):
        for estimate in self:
            if estimate.margin_type in ('percent', 'amount') and estimate.margin_value < 0:
                raise ValidationError(_('El margen no puede ser negativo.'))
            if estimate.margin_type == 'manual' and estimate.manual_sale_price < 0:
                raise ValidationError(_('El precio final no puede ser negativo.'))

    @api.constrains('date', 'date_validity')
    def _check_validity_date(self):
        for estimate in self:
            if estimate.date_validity and estimate.date_validity < estimate.date:
                raise ValidationError(_('La fecha de validez no puede ser anterior a la fecha del presupuesto.'))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('name') or values['name'] in (_('Nuevo'), 'New'):
                values['name'] = self.env['ir.sequence'].next_by_code('partyon.estimate') or _('Nuevo')
        return super().create(vals_list)

    def copy(self, default=None):
        values = dict(default or {})
        values.setdefault('name', _('Nuevo'))
        values.setdefault('sale_order_id', False)
        values.setdefault('approved_by', False)
        values.setdefault('approved_date', False)
        return super().copy(values)

    def action_review(self):
        for estimate in self:
            if estimate.state != 'draft':
                raise UserError(_('Solo se pueden enviar a revisión presupuestos en borrador.'))
            if not estimate.line_ids:
                raise UserError(_('Añada al menos una línea de coste antes de enviar a revisión.'))
            estimate.state = 'review'

    def action_approve(self):
        if not self.env.user.has_group('partyon_presupuestacion.group_partyon_manager'):
            raise AccessError(_('Solo un responsable de presupuestación puede aprobar.'))
        for estimate in self:
            if estimate.state != 'review':
                raise UserError(_('Solo se pueden aprobar presupuestos en revisión.'))
            estimate.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        for estimate in self:
            if estimate.state == 'customer_approved':
                raise UserError(_('No se puede cancelar un presupuesto aceptado por el cliente.'))
            estimate.state = 'cancel'

    def action_draft(self):
        for estimate in self:
            if estimate.sale_order_id and estimate.sale_order_id.state not in ('cancel',):
                raise UserError(_('Cancele primero la cotización vinculada.'))
            estimate.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
                'sale_order_id': False,
            })

    def action_apply_template(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Las plantillas solo se pueden aplicar en borrador.'))
        if not self.template_id:
            raise UserError(_('Seleccione una plantilla.'))
        commands = [fields.Command.clear()]
        commands.extend(
            fields.Command.create(line._prepare_estimate_line_values())
            for line in self.template_id.line_ids
        )
        # The template already contains the generated machine-cost lines.
        # Copy them as-is and prevent estimate-line.create() from generating
        # a second machine line for each source product.
        self.with_context(skip_machine_cost_generation=True).write({
            'line_ids': commands,
            'estimate_category_id': self.template_id.category_id.id,
            'margin_type': self.template_id.margin_type,
            'margin_value': self.template_id.margin_value,
            'manual_sale_price': self.template_id.manual_sale_price,
            'quote_detail_mode': self.template_id.quote_detail_mode,
        })

    def action_save_as_template(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo se pueden guardar como plantilla los presupuestos en borrador.'))
        template = self.env['partyon.estimate.template'].create({
            'name': self.estimate_name,
            'category_id': self.estimate_category_id.id,
            'company_id': self.company_id.id,
            'margin_type': self.margin_type,
            'margin_value': self.margin_value,
            'manual_sale_price': self.manual_sale_price,
            'quote_detail_mode': self.quote_detail_mode,
            'description': self.description,
            'line_ids': [fields.Command.create({
                'sequence': line.sequence,
                'line_type': line.line_type,
                'product_id': line.product_id.id,
                'name': line.name,
                'calculation_method': line.calculation_method,
                'manual_quantity': line.manual_quantity,
                'pieces': line.pieces,
                'width': line.width,
                'height': line.height,
                'depth': line.depth,
                'hours': line.hours,
                'time_unit_sel': line.time_unit_sel,
                'dimension_uom_id': line.dimension_uom_id.id,
                'waste_percent': line.waste_percent,
                'uom_id': line.uom_id.id,
                'cost_unit': line.cost_unit,
                'machine_time_total': line.machine_time_total,
            }) for line in self.line_ids if not line.is_machine_cost_line]
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Plantilla de presupuesto'),
            'res_model': 'partyon.estimate.template',
            'res_id': template.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_common_line_taxes(self):
        """Impuestos si TODAS las líneas comparten el mismo conjunto; vacío en
        caso contrario (o si ninguna línea tiene impuestos)."""
        self.ensure_one()
        common_taxes = None
        for line in self.line_ids:
            if common_taxes is None:
                common_taxes = line.tax_ids
            elif line.tax_ids != common_taxes:
                return self.env['account.tax']
        return common_taxes or self.env['account.tax']

    def _prepare_summary_sale_line(self):
        self.ensure_one()
        product = self.env.ref('partyon_presupuestacion.product_partyon_service')
        values = {
            'product_id': product.id,
            'name': self.estimate_name,
            'product_uom_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': self.sale_price,
            'purchase_price': self.subtotal_cost,
        }
        common_taxes = self._get_common_line_taxes()
        if common_taxes:
            values['tax_ids'] = [fields.Command.set(common_taxes.ids)]
        return values

    def _prepare_detailed_sale_lines(self):
        self.ensure_one()
        generic_product = self.env.ref('partyon_presupuestacion.product_partyon_service')
        values = []
        for line in self.line_ids:
            product = line.product_id or generic_product
            values.append({
                'product_id': product.id,
                'name': line.name,
                'product_uom_qty': line.quantity,
                'product_uom_id': line.uom_id.id or product.uom_id.id,
                'price_unit': line.sale_unit,
                'purchase_price': line.cost_unit,
                'tax_ids': [fields.Command.set(line.tax_ids.ids)],
            })
        return values

    def action_create_sale_order(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('El presupuesto debe estar aprobado para generar una cotización.'))
        if self.sale_order_id:
            raise UserError(_('Ya existe una cotización vinculada: %s') % self.sale_order_id.display_name)
        if not self.line_ids:
            raise UserError(_('No se puede cotizar un presupuesto sin líneas.'))
        line_values = (
            [self._prepare_summary_sale_line()]
            if self.quote_detail_mode == 'summary'
            else self._prepare_detailed_sale_lines()
        )
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'opportunity_id': self.opportunity_id.id,
            'validity_date': self.date_validity,
            'note': self.notes_customer,
            'partyon_estimate_id': self.id,
            'order_line': [fields.Command.create(values) for values in line_values],
        })
        self.write({'sale_order_id': sale_order.id, 'state': 'quoted'})
        return self.action_view_sale_order()

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No hay una cotización vinculada.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotización'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_new_version(self):
        self.ensure_one()
        new_estimate = self.copy({
            'parent_estimate_id': self.id,
            'version': self.version + 1,
            'state': 'draft',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva versión'),
            'res_model': 'partyon.estimate',
            'res_id': new_estimate.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_customer_approve(self):
        for estimate in self:
            if estimate.state != 'quoted':
                raise UserError(_('Solo se puede aceptar un presupuesto ya cotizado.'))
            estimate.state = 'customer_approved'

    def action_create_product_from_estimate(self):
        self.ensure_one()

        return {
            'name': 'Crear producto',
            'type': 'ir.actions.act_window',
            'res_model': 'product.from.estimate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_estimate_id': self.id}
        }