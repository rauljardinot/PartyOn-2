# ICA App Visibility

Módulo para Odoo 19 que permite controlar la visibilidad de las aplicaciones en el panel de inicio de `ica_web_responsive` por cada contacto (`res.partner`).

## Funcionamiento General

Por defecto, un contacto **no ve ninguna aplicación** en el panel de inicio. Un administrador debe asignar manualmente qué aplicaciones son visibles para cada contacto desde la pestaña "App Visibility" en el formulario del contacto.

Los administradores (`base.group_system`) siempre ven todas las aplicaciones.

---

## Arquitectura

### Backend (Python)

#### `models/res_partner.py`

**Clase `ResPartner`** — hereda `res.partner`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `visible_menu_ids` | Many2many → `ir.ui.menu` | Aplicaciones visibles para este contacto. Dominio: solo menús raíz (`parent_id = False`). Tabla intermedia: `ica_partner_app_visibility_rel`. |

#### `models/ir_http.py`

**Clase `IrHttp`** — hereda `ir.http`.

| Método | Descripción |
|--------|-------------|
| `session_info()` | Extiende el método de Odoo para inyectar `app_visibility` en la sesión JS. Para cada usuario calcula qué apps debe ocultar comparando todos los menús raíz con los que tiene asignados en su `partner_id.visible_menu_ids`. Los administradores siempre reciben `hidden_apps: []`. |

**Lógica de filtrado:**
```
hidden_apps = [todas las apps raíz] − [apps asignadas al contacto]
```
Si el contacto no tiene ninguna app asignada → `hidden_apps` contiene todas las apps → no ve nada.

---

### Frontend (JavaScript)

#### `static/src/app_visibility.esm.js`

**Parche del componente `HomeMenu`** de `ica_web_responsive`.

| Qué hace | Cómo |
|----------|------|
| Sobrescribe el getter `displayedApps` | Filtra `super.displayedApps` eliminando aquellas cuyo `xmlid` esté en `session.app_visibility.hidden_apps`. |
| Si `hidden_apps` está vacío | No filtra nada (el usuario ve todas las apps). |

Usa `patch()` de `@web/core/utils/patch` para extender el prototype de `HomeMenu` sin modificar el módulo original.

---

### Vistas (XML)

#### `views/res_partner_views.xml`

| Registro | Descripción |
|----------|-------------|
| `view_partner_form_app_visibility` | Hereda `base.view_partner_form`. Añade una pestaña "App Visibility" dentro del notebook del formulario de contacto, con el campo `visible_menu_ids` usando el widget `many2many_tags`. |

---

## Flujo Completo

```
1. Admin abre formulario de contacto → pestaña "App Visibility"
2. Admin escribe nombre de app en el campo tags → autocompleta menús raíz
3. Admin selecciona apps → se guardan en visible_menu_ids
4. Usuario inicia sesión → ir.http.session_info() calcula hidden_apps
5. JS recibe session.app_visibility.hidden_apps
6. HomeMenu.displayedApps filtra las apps ocultas
7. Usuario ve solo las apps asignadas en el panel de inicio
```

## Dependencias

- `ica_web_responsive` — módulo que crea el panel de inicio con los iconos de apps
- `base` — módulo estándar de Odoo

## Instalación

Instalar el módulo desde el menú de Aplicaciones. No requiere configuración adicional post-instalación. El módulo no modifica ningún archivo de otros módulos, solo hereda y parchea.
