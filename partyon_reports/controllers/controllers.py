# from odoo import http


# class PartyonReports(http.Controller):
#     @http.route('/partyon_reports/partyon_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/partyon_reports/partyon_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('partyon_reports.listing', {
#             'root': '/partyon_reports/partyon_reports',
#             'objects': http.request.env['partyon_reports.partyon_reports'].search([]),
#         })

#     @http.route('/partyon_reports/partyon_reports/objects/<model("partyon_reports.partyon_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('partyon_reports.object', {
#             'object': obj
#         })

