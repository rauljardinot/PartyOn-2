from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute("SELECT to_regclass('partyon_legacy_template_line')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        """
        SELECT template_id, sequence, product_id, name, quantity, uom_id,
               width, height, depth, cost_product_unit
          FROM partyon_legacy_template_line
         ORDER BY template_id, sequence
        """
    )
    env = api.Environment(cr, SUPERUSER_ID, {})
    Line = env['partyon.estimate.template.line']
    for row in cr.dictfetchall():
        template = env['partyon.estimate.template'].browse(row['template_id']).exists()
        if not template:
            continue
        product = env['product.product'].browse(row['product_id']).exists()
        Line.create({
            'template_id': template.id,
            'sequence': row['sequence'] or 10,
            'line_type': 'material',
            'product_id': product.id,
            'name': row['name'] or product.display_name or 'Línea migrada',
            'calculation_method': 'manual',
            'manual_quantity': row['quantity'] if row['quantity'] and row['quantity'] > 0 else 1.0,
            'pieces': 1.0,
            'width': row['width'] or 0.0,
            'height': row['height'] or 0.0,
            'depth': row['depth'] or 0.0,
            'uom_id': row['uom_id'],
            'cost_unit': row['cost_product_unit'] or 0.0,
        })
    cr.execute('DROP TABLE partyon_legacy_template_line')
