import { patch } from "@web/core/utils/patch";
import { HomeMenu } from "@ica_web_responsive/webclient/home_menu/home_menu";
import { session } from "@web/session";

patch(HomeMenu.prototype, {
    get displayedApps() {
        const apps = super.displayedApps;
        const hiddenApps = session.app_visibility?.hidden_apps;
        if (!hiddenApps || hiddenApps.length === 0) {
            return apps;
        }
        return apps.filter((app) => !hiddenApps.includes(app.xmlid));
    },
});
