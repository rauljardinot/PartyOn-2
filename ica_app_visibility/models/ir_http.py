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
            return session

        partner = user.partner_id
        visible_ids = set(partner.visible_menu_ids.ids)

        all_root = self.env["ir.ui.menu"].sudo().search([("parent_id", "=", False)])
        if not all_root:
            session["app_visibility"] = {"hidden_apps": []}
            return session

        IrModelData = self.env["ir.model.data"].sudo()
        xmlid_data = IrModelData.search_fetch(
            [("model", "=", "ir.ui.menu"), ("res_id", "in", all_root.ids)],
            ["res_id", "complete_name"],
        )
        xmlid_map = {d.res_id: d.complete_name for d in xmlid_data}

        hidden = [
            xmlid_map[menu.id]
            for menu in all_root
            if menu.id not in visible_ids and menu.id in xmlid_map
        ]

        session["app_visibility"] = {"hidden_apps": hidden}
        return session
