from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    centimeter = env.ref('uom.product_uom_cm')
    env['partyon.estimate.line'].search([
        ('calculation_method', 'in', ('area', 'volume')),
        ('dimension_uom_id', '=', False),
    ]).write({'dimension_uom_id': centimeter.id})
    env['partyon.estimate.template.line'].search([
        ('calculation_method', 'in', ('area', 'volume')),
        ('dimension_uom_id', '=', False),
    ]).write({'dimension_uom_id': centimeter.id})
