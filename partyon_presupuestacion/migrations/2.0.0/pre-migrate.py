def migrate(cr, version):
    cr.execute("SELECT to_regclass('partyon_estimate_line')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'partyon_estimate_line'
           AND column_name = 'template_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute('DROP TABLE IF EXISTS partyon_legacy_template_line')
    cr.execute(
        """
        CREATE TABLE partyon_legacy_template_line AS
        SELECT template_id, sequence, product_id, name, quantity, uom_id,
               width, height, depth, cost_product_unit
          FROM partyon_estimate_line
         WHERE template_id IS NOT NULL
        """
    )
    cr.execute(
        """
        DELETE FROM partyon_estimate_line
         WHERE template_id IS NOT NULL
           AND estimate_id IS NULL
        """
    )
