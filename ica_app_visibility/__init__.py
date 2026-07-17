from . import models


def _populate_app_visibility(env):
    env["ica.app.visibility"].sudo()._populate_from_menus()
