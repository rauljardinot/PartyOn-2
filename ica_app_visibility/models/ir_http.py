from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session = super().session_info()
        user = self.env.user
        if user._is_public() or not user.id:
            session["app_visibility"] = {"hidden_apps": []}
            return session

        if user.has_group("base.group_system") or user._is_admin():
            session["app_visibility"] = {"hidden_apps": []}
        else:
            visible_records = self.env["ica.app.visibility"].sudo().search(
                [("active", "=", True), ("group_ids", "!=", False)]
            )
            hidden = []
            for record in visible_records:
                if not any(group in user.groups_id for group in record.group_ids):
                    hidden.append(record.menu_xmlid)
            session["app_visibility"] = {"hidden_apps": hidden}
        return session
