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

    def test_estimate_area_product_keeps_calculation_method_on_create(self):
        area_product = self.env['product.product'].create({
            'name': 'Material de presupuesto por metro cuadrado',
            'standard_price': 7.5,
            'type': 'consu',
            'uom_id': self.uom_square_meter.id,
        })
        estimate = self._create_estimate(line_ids=[fields.Command.create({
            'product_id': area_product.id,
            'name': area_product.display_name,
            'width': 2.0,
            'height': 3.0,
            'dimension_uom_id': self.uom_meter.id,
            'pieces': 1.0,
            'uom_id': area_product.uom_id.id,
            'cost_unit': area_product.standard_price,
        })])
        line = estimate.line_ids.filtered(lambda item: item.product_id == area_product)
        self.assertEqual(line.calculation_method, 'area')
        self.assertAlmostEqual(line.quantity, 6.0)

    def test_fixed_and_manual_price(self):
        estimate = self._create_estimate(margin_type='amount', margin_value=50.0)
        self.assertAlmostEqual(estimate.subtotal_cost, 100.0)
        self.assertAlmostEqual(estimate.sale_price, 150.0)
        estimate.write({'margin_type': 'manual', 'manual_sale_price': 175.0})
        self.assertAlmostEqual(estimate.margin_amount, 75.0)
        self.assertAlmostEqual(estimate.margin_percent, 0.75)

    def test_line_taxes_flow_to_totals_pdf_and_sale_order(self):
        tax_21 = self.env['account.tax'].create({
            'name': 'IVA 21%',
            'amount': 21.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        taxed_product = self.env['product.product'].create({
            'name': 'Material con IVA',
            'standard_price': 100.0,
            'type': 'consu',
            'uom_id': self.uom_unit.id,
            'taxes_id': [fields.Command.set(tax_21.ids)],
        })
        estimate = self._create_estimate(line_ids=[fields.Command.create({
            'line_type': 'material',
            'product_id': taxed_product.id,
            'name': 'Material con IVA',
            'manual_quantity': 1.0,
            'uom_id': self.uom_unit.id,
            'cost_unit': 100.0,
        })])
        line = estimate.line_ids
        # El IVA se trae del producto y se calcula sobre la venta (130 con el 30% de margen)
        self.assertEqual(line.tax_ids, tax_21)
        self.assertAlmostEqual(line.sale_subtotal, 130.0)
        self.assertAlmostEqual(line.sale_tax_amount, 27.3)
        self.assertAlmostEqual(line.sale_total, 157.3)
        self.assertAlmostEqual(estimate.sale_tax_amount, 27.3)
        self.assertAlmostEqual(estimate.sale_total, 157.3)
        summary = estimate.get_tax_summary()
        self.assertEqual(len(summary), 1)
        self.assertAlmostEqual(summary[0]['base'], 130.0)
        self.assertAlmostEqual(summary[0]['amount'], 27.3)

        # Modo resumen: la línea única de la cotización recibe el IVA común
        estimate.action_review()
        estimate.action_approve()
        estimate.action_create_sale_order()
        sale_line = estimate.sale_order_id.order_line
        self.assertEqual(sale_line.tax_ids, tax_21)
        self.assertAlmostEqual(sale_line.price_subtotal, 130.0)
        self.assertAlmostEqual(sale_line.price_total, 157.3)

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

    def test_template_area_product_keeps_calculation_method_on_create(self):
        area_product = self.env['product.product'].create({
            'name': 'Material por metro cuadrado',
            'standard_price': 7.5,
            'type': 'consu',
            'uom_id': self.uom_square_meter.id,
        })
        template = self.env['partyon.estimate.template'].create({
            'name': 'Plantilla de área',
            'line_ids': [fields.Command.create({
                'product_id': area_product.id,
                'name': area_product.display_name,
                'width': 2.0,
                'height': 3.0,
                'dimension_uom_id': self.uom_meter.id,
                'pieces': 1.0,
                'uom_id': area_product.uom_id.id,
                'cost_unit': area_product.standard_price,
            })],
        })
        line = template.line_ids.filtered(lambda item: not item.is_machine_cost_line)
        self.assertEqual(line.calculation_method, 'area')
        self.assertAlmostEqual(line.quantity, 6.0)

    def test_template_line_uses_estimate_line_create_logic(self):
        machine_product = self.env['product.product'].create({
            'name': 'Coste de máquina de prueba',
            'standard_price': 8.0,
            'type': 'consu',
            'uom_id': self.uom_hour.id,
        })
        source_product = self.env['product.product'].create({
            'name': 'Material con máquina',
            'standard_price': 10.0,
            'type': 'consu',
            'uom_id': self.uom_unit.id,
            'need_machine_cost': True,
            'machine_time_per_unit': 2.0,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'partyon_presupuestacion.product_machine_cost_cnc', machine_product.id,
        )
        template = self.env['partyon.estimate.template'].create({
            'name': 'Plantilla con máquina',
            'line_ids': [fields.Command.create({
                'line_type': 'material',
                'product_id': source_product.id,
                'name': source_product.display_name,
                'manual_quantity': 3.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
                'machine_time_total': 6.0,
            })],
        })
        self.assertEqual(len(template.line_ids), 2)
        self.assertEqual(len(template.line_ids.filtered('is_machine_cost_line')), 1)
        estimate = self._create_estimate(template_id=template.id)
        estimate.action_apply_template()
        source_line = estimate.line_ids.filtered(lambda line: line.product_id == source_product)
        machine_line = estimate.line_ids.filtered(lambda line: line.product_id == machine_product)
        self.assertEqual(len(source_line), 1)
        self.assertEqual(len(machine_line), 1)
        self.assertEqual(machine_line.hours, 6.0)
        self.assertEqual(machine_line.quantity, 6.0)
        self.assertTrue(machine_line.is_machine_cost_line)

    def test_apply_template_copies_updated_machine_line_once(self):
        machine_product = self.env['product.product'].create({
            'name': 'Coste de máquina para plantilla',
            'standard_price': 8.0,
            'type': 'consu',
            'uom_id': self.uom_hour.id,
        })
        source_product = self.env['product.product'].create({
            'name': 'Producto con máquina en plantilla',
            'standard_price': 10.0,
            'type': 'consu',
            'uom_id': self.uom_unit.id,
            'need_machine_cost': True,
            'machine_time_per_unit': 2.0,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'partyon_presupuestacion.product_machine_cost_cnc', machine_product.id,
        )
        template = self.env['partyon.estimate.template'].create({
            'name': 'Plantilla con línea de máquina actualizada',
            'line_ids': [fields.Command.create({
                'line_type': 'material',
                'product_id': source_product.id,
                'name': source_product.display_name,
                'manual_quantity': 3.0,
                'pieces': 2.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
                'machine_time_total': 6.0,
            })],
        })
        template_machine_line = template.line_ids.filtered('is_machine_cost_line')
        template_machine_line.write({'hours': 12.0})

        estimate = self._create_estimate(template_id=template.id)
        estimate.action_apply_template()

        machine_lines = estimate.line_ids.filtered('is_machine_cost_line')
        source_line = estimate.line_ids.filtered(lambda line: line.product_id == source_product)
        self.assertEqual(len(machine_lines), 1)
        self.assertEqual(source_line.pieces, 2.0)
        self.assertEqual(machine_lines.hours, 12.0)
        self.assertEqual(machine_lines.quantity, 12.0)
        self.assertEqual(machine_lines.cost_subtotal, 96.0)

    def test_apply_template_copies_pieces_for_normal_product(self):
        area_product = self.env['product.product'].create({
            'name': 'Producto normal de plantilla',
            'standard_price': 5.0,
            'type': 'consu',
            'uom_id': self.uom_square_meter.id,
        })
        template = self.env['partyon.estimate.template'].create({
            'name': 'Plantilla de producto normal',
            'line_ids': [fields.Command.create({
                'line_type': 'material',
                'product_id': area_product.id,
                'name': area_product.display_name,
                'calculation_method': 'area',
                'pieces': 3.0,
                'width': 2.0,
                'height': 4.0,
                'dimension_uom_id': self.uom_meter.id,
                'uom_id': self.uom_square_meter.id,
                'cost_unit': 5.0,
            })],
        })
        estimate = self._create_estimate(template_id=template.id)
        estimate.action_apply_template()

        line = estimate.line_ids
        self.assertEqual(line.pieces, 3.0)
        self.assertEqual(line.quantity, 24.0)
        self.assertEqual(line.cost_subtotal, 120.0)

    def test_renting_discount_no_effect_when_not_for_renting(self):
        estimate = self._create_estimate(
            line_ids=[fields.Command.create({
                'line_type': 'material',
                'product_id': self.product.id,
                'name': 'Material principal',
                'manual_quantity': 10.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
                'discount_renting': 0.3,
            })],
        )
        line = estimate.line_ids
        self.assertFalse(estimate.is_for_renting)
        self.assertAlmostEqual(line.discount_renting, 0.3)
        self.assertAlmostEqual(line.sale_subtotal, 130.0)
        self.assertAlmostEqual(line.sale_unit, 13.0)
        self.assertAlmostEqual(line.margin_amount, 30.0)
        self.assertAlmostEqual(estimate.subtotal_cost, 100.0)
        self.assertAlmostEqual(estimate.sale_price, 130.0)

    def test_renting_discount_applies_per_line(self):
        tax_21 = self.env['account.tax'].create({
            'name': 'IVA 21%',
            'amount': 21.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        taxed_product = self.env['product.product'].create({
            'name': 'Material con IVA',
            'standard_price': 100.0,
            'type': 'consu',
            'uom_id': self.uom_unit.id,
            'taxes_id': [fields.Command.set(tax_21.ids)],
        })
        estimate = self._create_estimate(
            is_for_renting=True,
            line_ids=[fields.Command.create({
                'line_type': 'material',
                'product_id': taxed_product.id,
                'name': 'Material con IVA',
                'manual_quantity': 10.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
                'discount_renting': 0.3,
            })],
        )
        line = estimate.line_ids
        self.assertTrue(estimate.is_for_renting)
        self.assertAlmostEqual(line.cost_subtotal, 100.0)
        self.assertAlmostEqual(estimate.subtotal_cost, 100.0)
        self.assertAlmostEqual(estimate.sale_price, 130.0)
        self.assertAlmostEqual(line.sale_subtotal, 91.0)
        self.assertAlmostEqual(line.sale_unit, 9.1)
        self.assertAlmostEqual(line.margin_amount, -9.0)
        self.assertAlmostEqual(line.sale_tax_amount, 19.11)
        self.assertAlmostEqual(line.sale_total, 110.11)
        self.assertAlmostEqual(estimate.sale_tax_amount, 19.11)
        self.assertAlmostEqual(estimate.sale_total, 110.11)

        estimate.write({'is_for_renting': False})
        self.assertAlmostEqual(line.sale_subtotal, 130.0)
        self.assertAlmostEqual(line.sale_unit, 13.0)
        self.assertAlmostEqual(line.sale_total, 157.3)

    def test_renting_discount_recomputes_on_line_changes(self):
        estimate = self._create_estimate(
            is_for_renting=True,
            line_ids=[fields.Command.create({
                'line_type': 'material',
                'product_id': self.product.id,
                'name': 'Material principal',
                'manual_quantity': 10.0,
                'uom_id': self.uom_unit.id,
                'cost_unit': 10.0,
                'discount_renting': 0.3,
            })],
        )
        line = estimate.line_ids
        self.assertAlmostEqual(line.sale_subtotal, 91.0)
        self.assertAlmostEqual(line.sale_unit, 9.1)

        line.write({'manual_quantity': 20.0})
        self.assertAlmostEqual(line.quantity, 20.0)
        self.assertAlmostEqual(line.cost_subtotal, 200.0)
        self.assertAlmostEqual(estimate.subtotal_cost, 200.0)
        self.assertAlmostEqual(estimate.sale_price, 260.0)
        self.assertAlmostEqual(line.sale_subtotal, 182.0)
        self.assertAlmostEqual(line.sale_unit, 9.1)

        line.write({'discount_renting': 0.5})
        self.assertAlmostEqual(line.sale_subtotal, 130.0)
        self.assertAlmostEqual(line.sale_unit, 6.5)
        self.assertAlmostEqual(estimate.subtotal_cost, 200.0)
        self.assertAlmostEqual(estimate.sale_price, 260.0)

    def test_renting_discount_is_independent_per_line(self):
        estimate = self._create_estimate(
            is_for_renting=True,
            line_ids=[
                fields.Command.create({
                    'line_type': 'material',
                    'product_id': self.product.id,
                    'name': 'Material con descuento',
                    'manual_quantity': 10.0,
                    'uom_id': self.uom_unit.id,
                    'cost_unit': 10.0,
                    'discount_renting': 0.3,
                }),
                fields.Command.create({
                    'line_type': 'labor',
                    'name': 'Trabajo sin descuento',
                    'manual_quantity': 1.0,
                    'uom_id': self.uom_unit.id,
                    'cost_unit': 100.0,
                    'discount_renting': 0.0,
                }),
            ],
        )
        material_line = estimate.line_ids[0]
        labor_line = estimate.line_ids[1]
        self.assertAlmostEqual(estimate.subtotal_cost, 200.0)
        self.assertAlmostEqual(estimate.sale_price, 260.0)
        self.assertAlmostEqual(material_line.sale_subtotal, 91.0)
        self.assertAlmostEqual(material_line.sale_unit, 9.1)
        self.assertAlmostEqual(labor_line.sale_subtotal, 130.0)
        self.assertAlmostEqual(labor_line.sale_unit, 130.0)
        self.assertAlmostEqual(estimate.sale_tax_amount, 0.0)

    def test_estimate_can_be_saved_as_template(self):
        estimate = self._create_estimate(
            margin_type='amount',
            margin_value=25.0,
            quote_detail_mode='detail',
        )
        action = estimate.action_save_as_template()
        template = self.env['partyon.estimate.template'].browse(action['res_id'])
        self.assertEqual(template.name, estimate.estimate_name)
        self.assertEqual(template.margin_type, estimate.margin_type)
        self.assertEqual(template.margin_value, estimate.margin_value)
        self.assertEqual(template.quote_detail_mode, estimate.quote_detail_mode)
        self.assertEqual(len(template.line_ids), len(estimate.line_ids))
        self.assertEqual(template.line_ids.name, estimate.line_ids.name)

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
