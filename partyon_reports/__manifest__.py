{
    'name': "partyon_reports",

    'summary': "Reports adjustments for for partyon",

    'description': """
Reports adjustments for for partyon
    """,

    'author': 'PartyOn',
    'website': 'https://www.partyon.com',
    'license': 'LGPL-3',
    'category': 'Reports',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_template.xml'
    ]
}

