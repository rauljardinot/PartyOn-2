def migrate(cr, version):
    cr.execute("""
        UPDATE partyon_estimate
           SET margin_type = 'percent',
               margin_value = 0.0
         WHERE is_for_renting
           AND (
               margin_type IS DISTINCT FROM 'percent'
               OR margin_value IS DISTINCT FROM 0.0
           )
    """)

    cr.execute("""
        UPDATE partyon_estimate_line
           SET renting_benefit_percent = 0.0
         WHERE renting_benefit_percent IS NULL
    """)
