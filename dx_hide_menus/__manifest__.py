# -*- coding: utf-8 -*-
{
    'name': "hide_menus",

    'summary': """
       Ocultar el módulo Conversaciones, Contactos, Ventas""",

    'description': """
        Ocultar el módulo Conversaciones, Contactos, Ventas
    """,

    'author': "OdooNext: Raul Rolando Jardinot Gonzalez",
    'category': 'Uncategorized',
    'version': '0.1',
    "license": "LGPL-3",

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'mail', 'sale', 'hr', 'rt_activity_mgmt', 'calendar','bi_generic_import','prt_mail_messages'],

    # always loaded
    'data': [

        'security/security.xml',
        'views/menu.xml',
    ],
}
