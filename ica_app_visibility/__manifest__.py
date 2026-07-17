{
    "name": "ICA App Visibility",
    "version": "1.0",
    "category": "Hidden",
    "depends": ["ica_web_responsive", "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/app_visibility_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ica_app_visibility/static/src/app_visibility.esm.js",
        ],
    },
    "post_init_hook": "_populate_app_visibility",
    "author": "Simplicia Solutions",
    "website": "https://www.simpliciasolutions.com",
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
