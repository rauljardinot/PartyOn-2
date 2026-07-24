{
    'name': "ss_hide_menus",

    'summary': "Module to hide the menus to certain users",

    'description': """
Module to hide the menus to certain users
    """,

    'author': "Simplicia Solutions",
    'website': "https://www.simpliciasolutions.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'calendar', 'website_links', 'utm'],

    # always loaded
    'data': [
        'security/security.xml',
        'views/menu.xml',
    ]
}
