# -*- coding: utf-8 -*-
{
    'name': 'Mayor Precio de Compra',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Metodo de coste basado en el mayor precio de compra',
    'description': """
        Anade un metodo de coste que mantiene el coste del producto en el
        mayor precio unitario recibido en compras.
    """,
    'author': 'Raul Rolando Jardinot Gonzalez / Jose Carlos Luque Castro',
    'license': 'LGPL-3',
    'depends': ['stock_account', 'purchase_stock', ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
