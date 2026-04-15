# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PartyonEstimate(models.Model):
    _name = 'partyon.estimate'
    _description = 'Presupuestación Interna PartyOn'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    # -------------------------------------------------------------------------
    # CAMPOS PRINCIPALES
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
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
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        store=True,
    )
    date = fields.Date(
        string='Fecha',
        default=fields.Date.context_today,
        tracking=True,
    )
    date_validity = fields.Date(
        string='Válido hasta',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('review', 'En revisión'),
            ('approved', 'Aprobado'),
            ('quoted', 'Cotizado'),
            ('customer_approved', 'Aceptado por cliente'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # VERSIONADO
    # -------------------------------------------------------------------------
    version = fields.Integer(
        string='Versión',
        default=1,
        copy=False,
    )
    parent_estimate_id = fields.Many2one(
        'partyon.estimate',
        string='Versión anterior',
        copy=False,
    )
    child_estimate_ids = fields.One2many(
        'partyon.estimate',
        'parent_estimate_id',
        string='Versiones posteriores',
    )

    # -------------------------------------------------------------------------
    # LÍNEAS
    # -------------------------------------------------------------------------
    line_ids = fields.One2many(
        'partyon.estimate.line',
        'estimate_id',
        string='Líneas de presupuesto',
        copy=True,
    )

    # -------------------------------------------------------------------------
    # DESCRIPCIÓN Y NOTAS
    # -------------------------------------------------------------------------
    description = fields.Text(string='Descripción del trabajo')
    notes_internal = fields.Text(string='Notas internas')
    notes_customer = fields.Text(string='Notas para el cliente')

    # -------------------------------------------------------------------------
    # RELACIÓN CON VENTA Y PROYECTO
    # -------------------------------------------------------------------------
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Pedido de venta',
        copy=False,
        readonly=True,
    )
    sale_order_state = fields.Selection(
        related='sale_order_id.state',
        string='Estado del pedido',
    )
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        copy=False,
    )

    # -------------------------------------------------------------------------
    # CAMPOS COMPUTED — TOTALES DE COSTE
    # -------------------------------------------------------------------------
    total_material_cost = fields.Monetary(
        string='Coste de materiales',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_operation_cost = fields.Monetary(
        string='Coste de operaciones',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_labor_cost = fields.Monetary(
        string='Coste de mano de obra',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_overhead_cost = fields.Monetary(
        string='Costes generales',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_shipping_cost = fields.Monetary(
        string='Coste de envío',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_extra_cost = fields.Monetary(
        string='Costes extra',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    subtotal_cost = fields.Monetary(
        string='Subtotal coste',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    # -------------------------------------------------------------------------
    # MARGEN
    # -------------------------------------------------------------------------
    margin_type = fields.Selection(
        selection=[
            ('percent', 'Porcentaje'),
            ('amount', 'Importe fijo'),
            ('manual', 'Precio final manual'),
        ],
        string='Tipo de margen',
        default='percent',
    )
    margin_value = fields.Float(
        string='Valor del margen',
        help='Porcentaje (ej. 30 para 30%) o importe fijo según el tipo seleccionado.',
    )
    manual_sale_price = fields.Monetary(
        string='Precio de venta manual',
        currency_field='currency_id',
    )

    # -------------------------------------------------------------------------
    # PRECIOS FINALES COMPUTED
    # -------------------------------------------------------------------------
    suggested_sale_price = fields.Monetary(
        string='Precio sugerido',
        compute='_compute_sale_price',
        store=True,
        currency_field='currency_id',
    )
    sale_price = fields.Monetary(
        string='Precio de venta final',
        compute='_compute_sale_price',
        store=True,
        currency_field='currency_id',
    )
    margin_amount = fields.Monetary(
        string='Importe del margen',
        compute='_compute_sale_price',
        store=True,
        currency_field='currency_id',
    )
    margin_percent = fields.Float(
        string='% Margen',
        compute='_compute_sale_price',
        store=True,
    )

    # -------------------------------------------------------------------------
    # APROBACIÓN
    # -------------------------------------------------------------------------
    approved_by = fields.Many2one(
        'res.users',
        string='Aprobado por',
        copy=False,
        readonly=True,
    )
    approved_date = fields.Datetime(
        string='Fecha de aprobación',
        copy=False,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTED: TOTALES
    # -------------------------------------------------------------------------
    @api.depends(
        'line_ids.subtotal_material',
        'line_ids.subtotal_operation',
        'line_ids.subtotal_labor',
        'line_ids.subtotal_overhead',
        'line_ids.subtotal_shipping',
        'line_ids.subtotal_extra',
        'line_ids.line_subtotal',
    )
    def _compute_totals(self):
        for estimate in self:
            lines = estimate.line_ids
            estimate.total_material_cost = sum(lines.mapped('subtotal_material'))
            estimate.total_operation_cost = sum(lines.mapped('subtotal_operation'))
            estimate.total_labor_cost = sum(lines.mapped('subtotal_labor'))
            estimate.total_overhead_cost = sum(lines.mapped('subtotal_overhead'))
            estimate.total_shipping_cost = sum(lines.mapped('subtotal_shipping'))
            estimate.total_extra_cost = sum(lines.mapped('subtotal_extra'))
            estimate.subtotal_cost = sum(lines.mapped('line_subtotal'))

    # -------------------------------------------------------------------------
    # COMPUTED: PRECIO DE VENTA
    # -------------------------------------------------------------------------
    @api.depends('subtotal_cost', 'margin_type', 'margin_value', 'manual_sale_price')
    def _compute_sale_price(self):
        for estimate in self:
            subtotal = estimate.subtotal_cost
            margin_type = estimate.margin_type
            margin_value = estimate.margin_value

            if margin_type == 'percent':
                margin_amt = subtotal * (margin_value / 100.0)
                suggested = subtotal + margin_amt
            elif margin_type == 'amount':
                margin_amt = margin_value
                suggested = subtotal + margin_amt
            elif margin_type == 'manual':
                suggested = estimate.manual_sale_price
                margin_amt = suggested - subtotal
            else:
                margin_amt = 0.0
                suggested = subtotal

            estimate.suggested_sale_price = suggested
            estimate.sale_price = suggested
            estimate.margin_amount = margin_amt
            estimate.margin_percent = (
                (margin_amt / subtotal * 100.0) if subtotal else 0.0
            )

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'partyon.estimate'
                ) or 'New'
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = 'New'
        return super().copy(default)

    # -------------------------------------------------------------------------
    # ACCIONES DE FLUJO
    # -------------------------------------------------------------------------
    def action_review(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Solo se pueden enviar a revisión presupuestos en borrador.'))
            rec.state = 'review'

    def action_approve(self):
        for rec in self:
            if rec.state != 'review':
                raise UserError(_('Solo se pueden aprobar presupuestos en revisión.'))
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        for rec in self:
            if rec.state in ('customer_approved',):
                raise UserError(
                    _('No se puede cancelar un presupuesto ya aceptado por el cliente.')
                )
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
            })

    # -------------------------------------------------------------------------
    # GENERAR COTIZACIÓN DE VENTA
    # -------------------------------------------------------------------------
    def action_create_sale_order(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('El presupuesto debe estar aprobado para generar una cotización.'))
        if self.sale_order_id:
            raise UserError(
                _('Ya existe un pedido de venta vinculado: %s') % self.sale_order_id.name
            )

        order_lines = []
        for line in self.line_ids:
            product = line.product_id
            if not product:
                # Crear una línea con un producto genérico o sección
                product = self.env.ref(
                    'partyon_presupuestacion.product_partyon_service',
                    raise_if_not_found=False,
                )
            order_lines.append((0, 0, {
                'product_id': product.id if product else False,
                'name': line.name or (product.display_name if product else 'Línea de presupuesto'),
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id if line.uom_id else False,
                'price_unit': line.sale_price_unit,
            }))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'note': self.notes_customer,
            'order_line': order_lines,
        })

        self.write({
            'sale_order_id': sale_order.id,
            'state': 'quoted',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotización'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # VER PEDIDO DE VENTA
    # -------------------------------------------------------------------------
    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No hay ningún pedido de venta vinculado.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido de venta'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # NUEVA VERSIÓN
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # MARCAR ACEPTADO POR CLIENTE
    # -------------------------------------------------------------------------
    def action_customer_approve(self):
        for rec in self:
            if rec.state != 'quoted':
                raise UserError(
                    _('Solo se puede marcar como aceptado un presupuesto ya cotizado.')
                )
            rec.state = 'customer_approved'

