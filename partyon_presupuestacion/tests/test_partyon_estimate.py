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
            'waste_percent': 10.0,
            'uom_id': self.uom_unit.id,
            'cost_unit': 5.0,
        })])
        self.assertAlmostEqual(estimate.line_ids.quantity, 4.4)
        self.assertAlmostEqual(estimate.subtotal_cost, 22.0)
        self.assertAlmostEqual(estimate.sale_price, 28.6)
        self.assertAlmostEqual(estimate.margin_amount, 6.6)
        self.assertAlmostEqual(estimate.margin_percent, 0.3)

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
                'uom_id': self.uom_unit.id,
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
