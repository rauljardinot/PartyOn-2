from odoo import models, fields, api


class FormatTemplate(models.Model):
    _name = 'format.template'

    name = fields.Char(string='Nombre')
    prompt = fields.Html(string='Prompt Template')

