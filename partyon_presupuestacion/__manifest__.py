# -*- coding: utf-8 -*-
{
    'name': 'PartyOn Presupuestación',
    'version': '19.0.1.0.0',
    'category': 'Sales/Estimations',
    'summary': 'Presupuestación interna de trabajos personalizados para PartyOn',
    'description': """
        Módulo de presupuestación interna para calcular costes de piezas
        personalizadas antes de generar cotizaciones de venta.
    """,
    'author': 'PartyOn',
    'website': 'https://www.partyon.com',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'sale_management',
        'stock',
        'purchase',
        'account',
        'mail',
        'contacts',
        'project',
    ],
    'data': [
        'security/partyon_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/partyon_estimate_views.xml',
        'views/menu_views.xml',
    ],
    # 'demo': [
    #     'demo/product.category.csv',
    #     'demo/product.template.csv',
    # ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
