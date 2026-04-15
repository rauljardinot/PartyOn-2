# PartyOn-2
Company PartyOn

## Módulo: partyon_presupuestacion

Módulo de presupuestación interna para Odoo 19 que permite gestionar la etapa previa a la venta, calculando costes internos de trabajos personalizados para fiestas, eventos y decoración.

### Características principales

- **Presupuestos internos** (`partyon.estimate`) con flujo de estados: Borrador → En revisión → Aprobado → Cotizado → Aceptado por cliente
- **Líneas de detalle** (`partyon.estimate.line`) con cálculo automático de:
  - Coste de materiales (con dimensiones y uso proporcional)
  - Coste de desperdicio
  - Coste eléctrico y de máquina
  - Mano de obra (diseño + manipulación)
  - Pintura/acabado
  - Envío y gastos extra
- **Márgenes** configurables por porcentaje, importe fijo o precio manual (global o por línea)
- **Generación automática** de cotizaciones de venta (`sale.order`)
- **Versionado** de presupuestos
- **Multi-compañía** con reglas de seguridad
- **Integración** con CRM, Ventas, Inventario, Compras, Contabilidad y Proyectos
- **Chatter** y actividades para seguimiento

### Dependencias

`crm`, `sale_management`, `stock`, `purchase`, `account`, `mail`, `contacts`, `project`

### Instalación

1. Copiar la carpeta `partyon_presupuestacion` en la ruta de addons de Odoo
2. Actualizar la lista de aplicaciones
3. Instalar el módulo "PartyOn Presupuestación"
