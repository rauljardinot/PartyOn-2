# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests.common import TransactionCase


class TestPartyonEstimate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [
            fields.Command.link(cls.env.ref('partyon_presupuestacion.group_partyon_manager').id)
        ]
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente de prueba'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_cm = cls.env.ref('uom.product_uom_cm')
        cls.uom_meter = cls.env.ref('uom.product_uom_meter')
        cls.uom_square_meter = cls.env.ref('uom.product_uom_square_meter')
        cls.uom_square_foot = cls.env.ref('uom.product_uom_square_foot')
        cls.uom_litre = cls.env.ref('uom.product_uom_litre')
        cls.uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product = cls.env['product.product'].create({
            'name': 'Material de prueba',
            'standard_price': 10.0,
            'list_price': 20.0,
            'type': 'consu',
            'uom_id': cls.uom_unit.id,
        })

    def _create_estimate(self, **values):
        estimate_values = {
            'estimate_name': 'Figura personalizada',
            'partner_id': self.partner.id,
            'margin_type': 'percent',
            'margin_value': 30.0,
            'line_ids': [fields.Command.create({
                'line_type': 'material',
                'product_id': self.product.id,
                'name': 'Material principal',
                'manual_quantity': 10.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
            })],
        }
        estimate_values.update(values)
        return self.env['partyon.estimate'].create(estimate_values)

    def test_area_quantity_cost_and_percentage_margin(self):
        estimate = self._create_estimate(line_ids=[fields.Command.create({
            'line_type': 'material',
            'name': 'Lona impresa',
            'calculation_method': 'area',
            'pieces': 2.0,
            'width': 100.0,
            'height': 200.0,
            'dimension_uom_id': self.uom_cm.id,
            'waste_percent': 10.0,
            'uom_id': self.uom_square_meter.id,
            'cost_unit': 5.0,
        })])
        self.assertAlmostEqual(estimate.line_ids.quantity, 4.4)
        self.assertAlmostEqual(estimate.subtotal_cost, 22.0)
        self.assertAlmostEqual(estimate.sale_price, 28.6)
        self.assertAlmostEqual(estimate.margin_amount, 6.6)
        self.assertAlmostEqual(estimate.margin_percent, 0.3)

    def test_dimension_and_consumption_uom_conversion(self):
        estimate = self._create_estimate(line_ids=[
            fields.Command.create({
                'line_type': 'material',
                'name': 'Cartón por pie cuadrado',
                'calculation_method': 'area',
                'pieces': 1.0,
                'width': 1.0,
                'height': 2.0,
                'dimension_uom_id': self.uom_meter.id,
                'uom_id': self.uom_square_foot.id,
                'cost_unit': 2.0,
            }),
            fields.Command.create({
                'line_type': 'material',
                'name': 'Resina por litro',
                'calculation_method': 'volume',
                'pieces': 1.0,
                'width': 100.0,
                'height': 100.0,
                'depth': 100.0,
                'dimension_uom_id': self.uom_cm.id,
                'uom_id': self.uom_litre.id,
                'cost_unit': 0.5,
            }),
        ])
        area_line = estimate.line_ids.filtered(lambda line: line.calculation_method == 'area')
        volume_line = estimate.line_ids.filtered(lambda line: line.calculation_method == 'volume')
        self.assertAlmostEqual(area_line.quantity, 21.53)
        self.assertAlmostEqual(area_line.cost_subtotal, 43.06)
        self.assertAlmostEqual(volume_line.quantity, 1000.0)
        self.assertAlmostEqual(volume_line.cost_subtotal, 500.0)

    def test_product_uom_drives_dimensions_sale_and_stock(self):
        area_product = self.env['product.product'].create({
            'name': 'Cartón por metro cuadrado',
            'standard_price': 10.0,
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_square_meter.id,
        })
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        self.env['stock.quant']._update_available_quantity(
            area_product,
            warehouse.lot_stock_id,
            70.0,
        )

        onchange_line = self.env['partyon.estimate.line'].new()
        onchange_line.product_id = area_product
        onchange_line._onchange_product_id()
        self.assertEqual(onchange_line.calculation_method, 'area')
        self.assertEqual(onchange_line.uom_id, self.uom_square_meter)
        self.assertEqual(onchange_line.dimension_uom_id, self.uom_cm)
        self.assertEqual(onchange_line.cost_unit, 10.0)

        estimate = self._create_estimate(line_ids=[fields.Command.create({
            'line_type': 'material',
            'product_id': area_product.id,
            'name': area_product.display_name,
            'calculation_method': 'area',
            'pieces': 1.0,
            'width': 5.0,
            'height': 6.0,
            'dimension_uom_id': self.uom_meter.id,
            'uom_id': self.uom_square_meter.id,
            'cost_unit': 10.0,
        })])
        line = estimate.line_ids
        self.assertEqual(line.quantity, 30.0)
        self.assertEqual(line.cost_subtotal, 300.0)
        self.assertEqual(line.available_quantity, 70.0)
        self.assertEqual(line.remaining_quantity, 40.0)
        self.assertEqual(line.shortage_quantity, 0.0)

        estimate.quote_detail_mode = 'detail'
        estimate.action_review()
        estimate.action_approve()
        estimate.action_create_sale_order()
        sale_line = estimate.sale_order_id.order_line
        self.assertEqual(sale_line.product_id, area_product)
        self.assertEqual(sale_line.product_uom_qty, 30.0)
        self.assertEqual(sale_line.product_uom_id, self.uom_square_meter)
        estimate.sale_order_id.action_confirm()
        self.assertEqual(area_product.qty_available, 70.0)
        self.assertEqual(area_product.virtual_available, 40.0)

    def test_fixed_and_manual_price(self):
        estimate = self._create_estimate(margin_type='amount', margin_value=50.0)
        self.assertAlmostEqual(estimate.subtotal_cost, 100.0)
        self.assertAlmostEqual(estimate.sale_price, 150.0)
        estimate.write({'margin_type': 'manual', 'manual_sale_price': 175.0})
        self.assertAlmostEqual(estimate.margin_amount, 75.0)
        self.assertAlmostEqual(estimate.margin_percent, 0.75)

    def test_template_lines_are_copied(self):
        template = self.env['partyon.estimate.template'].create({
            'name': 'Cartel estándar',
            'margin_type': 'amount',
            'margin_value': 25.0,
            'line_ids': [fields.Command.create({
                'line_type': 'labor',
                'name': 'Diseño',
                'calculation_method': 'hours',
                'hours': 3.0,
                'pieces': 1.0,
                'uom_id': self.uom_hour.id,
                'cost_unit': 12.0,
            })],
        })
        estimate = self._create_estimate(template_id=template.id)
        template_line = template.line_ids
        estimate.action_apply_template()
        self.assertEqual(len(estimate.line_ids), 1)
        self.assertNotEqual(estimate.line_ids.id, template_line.id)
        self.assertEqual(template_line.template_id, template)
        self.assertEqual(estimate.line_ids.name, 'Diseño')
        self.assertEqual(estimate.margin_type, 'amount')

    def test_summary_sale_order_uses_sale_price_and_internal_cost(self):
        estimate = self._create_estimate()
        estimate.action_review()
        estimate.action_approve()
        estimate.action_create_sale_order()
        sale_order = estimate.sale_order_id
        self.assertEqual(estimate.state, 'quoted')
        self.assertEqual(sale_order.partyon_estimate_id, estimate)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertAlmostEqual(sale_order.order_line.price_unit, 130.0)
        self.assertAlmostEqual(sale_order.order_line.purchase_price, 100.0)

    def test_detailed_sale_order_distributes_fixed_margin(self):
        estimate = self._create_estimate(
            margin_type='amount',
            margin_value=30.0,
            quote_detail_mode='detail',
            line_ids=[
                fields.Command.create({
                    'line_type': 'material', 'name': 'Material',
                    'manual_quantity': 1.0, 'uom_id': self.uom_unit.id,
                    'cost_unit': 100.0,
                }),
                fields.Command.create({
                    'line_type': 'labor', 'name': 'Trabajo',
                    'manual_quantity': 1.0, 'uom_id': self.uom_unit.id,
                    'cost_unit': 50.0,
                }),
            ],
        )
        estimate.action_review()
        estimate.action_approve()
        estimate.action_create_sale_order()
        self.assertEqual(len(estimate.sale_order_id.order_line), 2)
        self.assertAlmostEqual(sum(estimate.sale_order_id.order_line.mapped('price_subtotal')), 180.0)
