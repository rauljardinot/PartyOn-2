# -*- coding: utf-8 -*-
{
    'name': 'Highest Purchase Cost',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Inventory costing based on the highest purchase price',
    'description': """
        Adds an inventory costing method that keeps the product cost at the
        highest unit purchase price received in validated incoming stock moves.
    """,
    'author': 'Raul Rolando Jardinot Gonzalez / Jose Carlos Luque Castro',
    'maintainer': 'Raul Rolando Jardinot Gonzalez',
    'website': 'https://www.partyon.com',
    'license': 'LGPL-3',
    'depends': [
        'stock_account',
        'purchase_stock',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'icon': '/highest_purchase_cost/static/description/icon.png',
}
