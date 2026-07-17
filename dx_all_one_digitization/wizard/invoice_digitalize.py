# models/models.py
import json
import logging

from fuzzywuzzy import fuzz
from odoo import fields, models, _

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
_logger = logging.getLogger(__name__)


class InvoiceDigitalize(models.TransientModel):
    _name = 'invoice.digitalize'
    _description = 'Digitalizar Factura'

    file = fields.Binary(string='Attach file', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Adjuntar Archivo')
    filename = fields.Char(string='Name of file')
    create_partner = fields.Boolean(string='Create Partner?', default=True)
    create_product = fields.Boolean(string='Create Product?', default=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    match_product = fields.Boolean(string='Try Match Product?', default=True)
    include_taxes = fields.Boolean(string='Include Taxes?', default=True)
    format_template = fields.Many2one('format.template', string='Format Template ')



    def action_accept(self):
        id = self.env.context.get('active_ids')
        
        # If no active invoice, create a new one with the correct type from context
        if not id:
            move_type = self.env.context.get('default_move_type', 'out_invoice')            
            invoice = self.env['account.move'].create({
                'move_type': move_type,
            })
            id = [invoice.id]
        
        invoice = self.env['account.move'].browse(id)
        attachment_id = self.env['ir.attachment'].create({
            'name': self.filename,
            'datas': self.file,
            'res_model': 'account.move',
            'res_id': id[0] if id else False,
            'type': 'binary'
        })
        currency_id = self._context.get('currency_id', False)
        if not currency_id:
            currency_id = self.currency_id
        moves = []
        self.attachment_id = attachment_id
        for attachment_id in self.attachment_id:
            config_settings = self.env['res.config.settings']
            system_prompt = self._generate_system_prompt(invoice_type=invoice.move_type)
            user_prompt = config_settings._get_text_file_contents(attachment_id)
            conversation_history = [{'role': 'system', 'content': system_prompt}]
            response = config_settings.generate_text_olg_api(user_prompt, conversation_history)
            try:
                response_dict = json.loads(response)
            except json.decoder.JSONDecodeError:
                fixed_json = config_settings._fix_json(response)
                response_dict = json.loads(fixed_json)

            partner_id = config_settings._get_partner_from_response(response_dict, self.create_partner)

            line_ids = self._get_invoice_lines(response_dict, invoice.move_type)
            ref = response_dict.get('reference') or response_dict.get('reference') or response_dict.get(
                'document_number')

            invoice_date = False
            invoice_date_due = False
            try:
                invoice_date = fields.Date.to_string(fields.Date.to_date(response_dict.get('invoice_date')))
            except:
                invoice_date = False
            try:
                invoice_date_due = fields.Date.to_string(fields.Date.to_date(response_dict.get('due_date')))
            except:
                invoice_date_due = False

            extracted_values = {
                'ref': str(ref),
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date_due,
                'payment_reference': response_dict.get('payment_reference') or False,
                'invoice_line_ids': line_ids,
                'narration': response_dict.get('notes'),
                'partner_id': partner_id and partner_id.id,
                'currency_id': currency_id.id,
            }
            if currency_id:
                extracted_values['currency_id'] = currency_id.id
            invoice.write(extracted_values)
            moves.append(invoice)
        action_vals = {
            'name': _('Generated Documents'),
            'domain': [('id', 'in',  [m.id for m in moves])],
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'context': self._context
        }
        if len(moves) == 1:
            action_vals.update({
                'views': [[False, "form"]],
                'view_mode': 'form',
                'res_id': moves[0].id,
            })
        else:
            action_vals.update({
                'views': [[False, "tree"], [False, "kanban"], [False, "form"]],
                'view_mode': 'tree, kanban, form',
            })
        return action_vals

    def _generate_system_prompt(self, invoice_type):
        partner_type, document_type, company_type = False, False, False
        invoice_type_line = ""

        if invoice_type == 'in_invoice':
            partner_type, document_type, company_type = 'vendor', 'bill', 'customer'
        elif invoice_type == 'out_invoice':
            partner_type, document_type, company_type = 'customer', 'invoice', 'vendor'
        elif invoice_type == 'out_refund':
            partner_type, document_type, company_type = 'customer', 'credit note', 'vendor'
        elif invoice_type == 'in_refund':
            partner_type, document_type, company_type = 'vendor', 'credit note', 'customer'

        if all([partner_type, document_type, company_type]):
            invoice_type_line = f"""The record pertains to {partner_type} {document_type} directed to {company_type} {self.env.company.name}. You'll discover information about the {partner_type} (partner) and its specifics. Exercise caution to avoid conflating vendor and customer details."""

        prompt = f"""You are an invoice digitizer.
        I will receive content extracted through OCR from a document.
        The content will undergo an initial check to identify and rectify errors introduced by OCR.
        Subsequently, relevant values will be extracted and used to populate the JSON structure below.
        Don't repeat products if they aren't already repeated; analyze the product lines to avoid mistakes.
        The product names can be large.
        {invoice_type_line}
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
             "invoice_date": "YYYY-MM-DD",
             "due_date": "YYYY-MM-DD",
             "invoice_lines": [
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

    def _get_invoice_lines(self, response_dict, move_type):
        line_ids = []
        for line in response_dict.get('invoice_lines', []):
            quantity = float(line.get('quantity', 0)) if line.get('quantity') else 0
            price_unit = float(line.get('price_unit', 0)) if line.get('price_unit') else 0
            discount = float(line.get('discount', 0)) if line.get('discount') else 0
            tax_rate = float(line.get('tax_rate', 0)) if line.get('tax_rate') else 0
            tax_id = False
            type_tax_use = 'purchase' if move_type in ('in_invoice', 'in_refund') else 'sale'
            if self.include_taxes:
                tax_domain = [('type_tax_use', '=', type_tax_use), ('amount', '=', tax_rate), ('amount', '!=', 0.0),
                              ('active', '=', True)]
                tax_id = self.env['account.tax'].search(tax_domain, limit=1) if tax_rate else False
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
                'quantity': quantity,
                'price_unit': price_unit,
                'discount': discount,
                'tax_ids': tax_id and [(6, 0, tax_id.ids)]
            }))

        return line_ids

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
