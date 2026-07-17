from odoo import api, fields, models


class AppVisibility(models.Model):
    _name = "ica.app.visibility"
    _description = "App Visibility"
    _order = "sequence, id"

    name = fields.Char(
        string="App Name",
        compute="_compute_name",
        store=True,
    )
    menu_xmlid = fields.Char(
        string="Menu XML ID",
        required=True,
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ica_app_visibility_group_rel",
        column1="visibility_id",
        column2="group_id",
        string="Visible To Groups",
        help="If empty, the app is visible to everyone. "
        "If groups are set, only users in those groups see the app.",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )

    _sql_constraints = [
        (
            "menu_xmlid_unique",
            "UNIQUE(menu_xmlid)",
            "An app with this Menu XML ID already exists.",
        ),
    ]

    @api.depends("menu_xmlid")
    def _compute_name(self):
        for record in self:
            if record.menu_xmlid:
                menu = self._get_menu_from_xmlid(record.menu_xmlid)
                record.name = menu.name if menu else record.menu_xmlid
            else:
                record.name = ""

    def _get_menu_from_xmlid(self, xmlid):
        if not xmlid or "." not in xmlid:
            return False
        module, name = xmlid.rsplit(".", 1)
        ref = self.env["ir.model.data"].sudo().search(
            [("module", "=", module), ("name", "=", name), ("model", "=", "ir.ui.menu")],
            limit=1,
        )
        if ref:
            return self.env["ir.ui.menu"].sudo().browse(ref.res_id)
        return False

    @api.model
    def _populate_from_menus(self):
        root_menu = self.env.ref("base.menu_root", raise_if_not_found=False)
        if not root_menu:
            return 0
        IrModelData = self.env["ir.model.data"].sudo()
        apps = self.env["ir.ui.menu"].search([("parent_id", "=", root_menu.id)])
        existing_xmlids = set(self.search([]).mapped("menu_xmlid"))
        to_create = []
        for app in apps:
            data = IrModelData.search(
                [("model", "=", "ir.ui.menu"), ("res_id", "=", app.id)],
                limit=1,
            )
            if not data:
                continue
            xmlid = f"{data.module}.{data.name}"
            if xmlid in existing_xmlids:
                continue
            to_create.append(
                {
                    "menu_xmlid": xmlid,
                    "sequence": app.sequence or 10,
                }
            )
            existing_xmlids.add(xmlid)
        if to_create:
            self.create(to_create)
        return len(to_create)

    def action_populate_apps(self):
        count = self._populate_from_menus()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Apps Populated",
                "message": f"{count} new app(s) added to the visibility list.",
                "type": "success",
                "sticky": False,
            },
        }
