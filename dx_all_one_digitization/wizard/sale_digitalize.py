# models/models.py
import json
import logging

from fuzzywuzzy import fuzz
from odoo import fields
from odoo import models

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
_logger = logging.getLogger(__name__)


class SaleDigitalize(models.TransientModel):
    _name = 'sale.digitalize'
    _description = 'Digitalizar Factura'

    file = fields.Binary(string='Attach file', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Adjuntar Archivo')
    filename = fields.Char(string='Nombre de Archivo')
    create_partner = fields.Boolean(string='Create Partner?', default=True)
    create_product = fields.Boolean(string='Create Product?', default=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    match_product = fields.Boolean(string='Try Match Product?', default=True)
    include_taxes = fields.Boolean(string='Include Taxes?', default=False)
    format_template = fields.Many2one('format.template', string='Format Template ')

    def action_accept(self):
        config_settings = self.env['res.config.settings']

        if self.file:
            id = self.env.context.get('active_ids', [])
            if id:
                sale_order = self.env['sale.order'].browse(id)
            else:
                partner_id = self.env['res.partner'].search([], limit=1)
                sale_order = self.env['sale.order'].create(
                    {'partner_id': partner_id.id, 'company_id': self.env.company.id})
            self.attachment_id = self.env['ir.attachment'].create({
                    'name': self.filename,
                    'datas': self.file,
                    'res_model': 'sale.order',
                    'res_id': id[0] if id else False,
                    'type': 'binary'
                })


            system_prompt = self._generate_system_prompt()
            user_prompt = config_settings._get_text_file_contents(self.attachment_id)
            conversation_history = [{'role': 'system', 'content': system_prompt}]
            response = config_settings.generate_text_olg_api(user_prompt, conversation_history)
            try:
                response_dict = json.loads(response)
            except json.decoder.JSONDecodeError:
                fixed_json = config_settings._fix_json(response)
                response_dict = json.loads(fixed_json)

            partner_id = config_settings._get_partner_from_response(response_dict,self.create_partner )

            line_ids = self._get_sale_order_lines(response_dict)
            ref = response_dict.get('reference') or response_dict.get('reference') or response_dict.get(
                'document_number')

            due_date = False
            sale_date = False
            try:
                due_date = fields.Date.to_string(fields.Date.to_date(response_dict.get('due_date')))
            except:
                due_date = False

            try:
                sale_date = fields.Date.to_string(fields.Date.to_date(response_dict.get('sale_date')))
            except:
                sale_date = False

            extracted_values = {
                'client_order_ref': str(ref),
                #'date_order': sale_date,
                #'validity_date': due_date,
                'order_line': line_ids,
                'note': response_dict.get('notes'),
            }
            if partner_id:
                extracted_values['partner_id'] = partner_id.id
            if ref:
                extracted_values['client_order_ref'] = str(ref)
            if sale_date:
                extracted_values['date_order'] = sale_date
            if due_date:
                extracted_values['validity_date'] = due_date

            sale_order.write(extracted_values)
            return sale_order


    def _generate_system_prompt(self, ):
        partner_type, document_type, company_type = False, False, False
        sale_type_line = 'vendor', 'bill', 'customer'

        if all([partner_type, document_type, company_type]):
            sale_type_line = f"""The record pertains to {partner_type} {document_type} directed to {company_type} {self.env.company.name}. You'll discover information about the {partner_type} (partner) and its specifics. Exercise caution to avoid conflating vendor and customer details."""

        prompt = f"""You are an sale order digitizer.
        I will receive content extracted through OCR from a document.
        The content will undergo an initial check to identify and rectify errors introduced by OCR.
        Subsequently, relevant values will be extracted and used to populate the JSON structure below.
        Don't repeat line of products if they aren't already repeated; analyze the product lines to avoid mistakes.
        The product names can be large.
        {sale_type_line}
        Fill the values in the json with the right data types       
        Do not add any explanations and ``` tags.
        Just furnish a JSON object that is valid and conforms to the specified structure.        
        """ + """        
        {      
             "partner": {
                "name": "String",
                "vat_id": "String"
                "email": "String"
             },            
             "reference": "String",
             "document_number": "String",
             "sale_date": "YYYY-MM-DD",
             "due_date": "YYYY-MM-DD",
             "sale_order_lines": [
                 {
                     "product": "String",
                     "quantity": Float,
                     "price_unit": Float,
                     "discount": Float,
                     "tax_rate": Float,
                 },
             ],
             "notes": "String"
        } 
        """
        if self.format_template:
            prompt += "." + self.format_template.prompt
        return " ".join(prompt.split())



    def _get_sale_order_lines(self, response_dict):
        line_ids = []
        for line in response_dict.get('sale_order_lines', []):
            quantity = float(line.get('quantity', 0)) if line.get('quantity') else 0
            price_unit = float(line.get('price_unit', 0)) if line.get('price_unit') else 0
            discount = float(line.get('discount', 0)) if line.get('discount') else 0
            vat_rate = float(line.get('tax_rate', 0)) if line.get('tax_rate') else 0
            type_tax_use = 'sale'
            tax_id = False
            if self.include_taxes:
                tax_domain = [('type_tax_use', '=', type_tax_use), ('amount', '=', vat_rate), ('amount', '!=', 0.0),
                              ('active', '=', True)]
                tax_id = self.env['account.tax'].search(tax_domain, limit=1) if vat_rate else False
            all_product_ids = self.env['product.product'].search([])

            best_match_product = False
            if self.match_product:
                all_product_ids = self.env['product.product'].search([])
                if all_product_ids:
                    product_name_from_response = line.get('product')
                    threshold_similarity = 90
                    length_tolerance = 5
                    filtered_products = [
                        product for product in all_product_ids
                        if fuzz.ratio(product_name_from_response, product.name) >= threshold_similarity
                        and abs(len(product_name_from_response) - len(product.name)) <= length_tolerance
                    ]
                    if filtered_products:
                        # Si hay al menos una coincidencia que cumple con el umbral, toma la primera como mejor coincidencia
                        best_match_product = filtered_products[0]

            if not best_match_product and self.create_product:
                product_template = self.env['product.template'].create({
                    'name': line.get('product'),
                    'list_price': price_unit,
                })
                best_match_product = product_template.product_variant_id

            line_ids.append((0, 0, {
                'product_id': best_match_product.id if best_match_product else False,
                'name': line.get('product'),
                'product_uom_qty': quantity,
                'price_unit': price_unit,
                'discount': discount,
                'tax_ids': tax_id and [(6, 0, tax_id.ids)]  # Convert to Odoo format
            }))

        return line_ids

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}


