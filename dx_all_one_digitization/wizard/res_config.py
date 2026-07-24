import base64
import io
import json
import logging
try:
    from litellm import completion
except ImportError:
    completion = None
import uuid
import cv2
import numpy as np
import pytesseract
import requests
from PIL import Image, ImageOps
from fuzzywuzzy import fuzz
from odoo import _, fields
from odoo import models
from odoo.exceptions import UserError
from pdf2image import convert_from_bytes
from pypdf import PdfReader

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
_logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente OpenRouter compatible con Python 3.7"""

    def __init__(self, api_key, base_url="https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, model, messages, **kwargs):
        headers = {
            "Authorization": "Bearer %s" % self.api_key,
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        payload.update(kwargs)
        resp = requests.post(
            "%s/chat/completions" % self.base_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()


def _preprocess_image(image):
    image_array = np.asarray(image)
    channels = image_array.shape[-1] if image_array.ndim == 3 else 1

    if channels == 3:
        image = cv2.resize(image_array, None, fx=2, fy=2,
                           interpolation=cv2.INTER_CUBIC)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((5, 5), np.uint8)
        image = cv2.erode(image, kernel, iterations=1)
    return image

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_provider = fields.Selection([
        ('odoo_ai', 'Odoo AI'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('gemini', 'Gemini'),
        ('openrouter', 'OpenRouter'),
    ], string="AI Provider", default='odoo_ai', config_parameter='dx_all_one_digitization.ai_provider')

    api_key = fields.Char(string="API Key", config_parameter='dx_all_one_digitization.api_key')
    model_name = fields.Char(string="Model Name", config_parameter='dx_all_one_digitization.model_name')

    def generate_text_olg_api(self, prompt, conversation_history=[]):
        ai_provider = self.env['ir.config_parameter'].sudo().get_param('dx_all_one_digitization.ai_provider', 'odoo_ai')
        
        if ai_provider == 'odoo_ai':
            try:
                IrConfigParameter = self.env['ir.config_parameter'].sudo()
                olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
                response = self.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                    'prompt': prompt,
                    'conversation_history': conversation_history or [],
                    'version': "17.0",
                }, timeout=30)
                if response['status'] == 'success':
                    return response['content']
                elif response['status'] == 'error_prompt_too_long':
                    raise UserError(_("Sorry, your prompt is too long. Try to say it in fewer words."))
                else:
                    raise UserError(_("Sorry, we could not generate a response. Please try again later."))
            except Exception as e:
                raise UserError(_("Oops, it looks like our AI is unreachable!." + str(e))   )

        if ai_provider == 'openrouter':
            api_key = self.env['ir.config_parameter'].sudo().get_param('dx_all_one_digitization.api_key')
            if not api_key:
                raise UserError(_("API Key is missing. Please configure it in settings."))

            model_name = self.env['ir.config_parameter'].sudo().get_param('dx_all_one_digitization.model_name')

            messages = conversation_history or []
            messages.append({"role": "user", "content": prompt})

            try:
                client = LLMClient(api_key=api_key)
                response = client.chat(
                    model=model_name or 'openai/gpt-4o',
                    messages=messages,
                    temperature=0.0,
                )
                return response['choices'][0]['message']['content']
            except Exception as e:
                raise UserError(_("AI Provider Error: %s") % str(e))

        # LiteLLM Logic
        if not completion:
            raise UserError(_("LiteLLM library is not installed. Please install it to use external providers."))

        api_key = self.env['ir.config_parameter'].sudo().get_param('dx_all_one_digitization.api_key')
        if not api_key:
            raise UserError(_("API Key is missing. Please configure it in settings."))

        model_name = self.env['ir.config_parameter'].sudo().get_param('dx_all_one_digitization.model_name')
        
        # Construct model string for LiteLLM
        # Format: provider/model_name
        if ai_provider == 'openai':
            model = f"openai/{model_name or 'gpt-3.5-turbo'}"
        elif ai_provider == 'anthropic':
            model = f"anthropic/{model_name or 'claude-3-haiku-20240307'}"
        elif ai_provider == 'gemini':
            # LiteLLM uses 'gemini/...' for Google AI Studio
            model = f"gemini/{model_name or 'gemini-pro'}"
        else:
            raise UserError(_("Unsupported provider: %s") % ai_provider)

        messages = conversation_history or []
        # Ensure prompt is in messages
        messages.append({"role": "user", "content": prompt})

        try:
            # Call LiteLLM
            # GPT-5 models only support temperature=1
            temperature = 1.0 if model_name and 'gpt-5' in model_name.lower() else 0.0
            
            response = completion(
                model=model,
                messages=messages,
                api_key=api_key,
                temperature=temperature
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            raise UserError(_("AI Provider Error: " + str(e)))

    def iap_jsonrpc(self, url, method='call', params=None, timeout=15):
        """
        Calls the provided JSON-RPC endpoint, unwraps the result and
        returns JSON-RPC errors as exceptions.
        """

        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': uuid.uuid4().hex,
        }

        _logger.info('iap jsonrpc %s', url)
        try:
            req = requests.post(url, json=payload, timeout=timeout)
            req.raise_for_status()
            response = req.json()
            _logger.info("iap jsonrpc %s answered in %s seconds", url, req.elapsed.total_seconds())
            if 'error' in response:
                name = response['error']['data'].get('name').rpartition('.')[-1]
                message = response['error']['data'].get('message')
                if name == 'InsufficientCreditError':
                    e_class = UserError
                elif name == 'AccessError':
                    e_class = UserError
                elif name == 'UserError':
                    e_class = UserError
                else:
                    raise requests.exceptions.ConnectionError()
                e = e_class(message)
                e.data = response['error']['data']
                raise e
            return response.get('result')
        except (
                ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError) as e:
            raise UserError(
                _('The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was %s',
                  url)
            )

    def _image2text(self, f):
        try:
            img = Image.open(f)
        except AttributeError:
            img = f

        img = _preprocess_image(img)

        langs = '+'.join(pytesseract.get_languages())
        text = pytesseract.image_to_string(img, lang=langs)
        return text

    def data_segmentation(self, img):
        """
        Function to do segmentation for the retrieved data after converting it
        into image.
        :param img: The image format of the document that need to undergo the
        segmentation procedure.
        :return: The segments of the image.
        """
        img = ImageOps.grayscale(img)
        img = img.point(lambda x: 255 if x > 176 else 0, '1')
        img_rgb = ImageOps.invert(img.convert("RGB"))
        segments = []
        segment_bounds = img_rgb.getbbox()
        while segment_bounds:
            segment = img_rgb.crop(segment_bounds)
            if segment.size[0] > 0 and segment.size[1] > 0:
                segments.append(segment)
            img_rgb = ImageOps.crop(img_rgb, segment_bounds)
            segment_bounds = img_rgb.getbbox()
        return segments

    def _process_image(self, f):
        # Load image
        try:
            image = Image.open(f)
        except AttributeError:
            image = f
        # Convert image to NumPy array
        image_array = np.asarray(image)
        # Check the number of channels
        channels = image_array.shape[-1] if image_array.ndim == 3 else 1
        # Resize and convert to grayscale using Pillow
        if channels == 3:
            pil_image = Image.fromarray(image_array)
            resized_image = pil_image.resize((image_array.shape[1] * 2, image_array.shape[0] * 2), Image.LANCZOS)
            gray_image = ImageOps.grayscale(resized_image)
            # Convert back to NumPy array
            processed_image = np.asarray(gray_image)
        else:
            processed_image = image_array

        return processed_image

    def _get_text_file_contents(self,attachment_id):
        attachment_data = ''
        content = base64.b64decode(attachment_id.with_context(bin_size=False).datas)
        f = io.BytesIO(content)
        if 'pdf' in attachment_id.mimetype:
            parsed_data = self._get_text_pdf(f)
            if parsed_data == '':
                images = convert_from_bytes(content, dpi=300)
                for image in images:
                    parsed_data += self._image2text(image)
            attachment_data += f'--- {parsed_data} --- '
        elif 'image' in attachment_id.mimetype:
            attachment_data += f'--- {self._image2text(f)} --- '
        return " ".join(attachment_data.split())

    def _get_text_pdf(self, f):
        parsed_data = ''
        reader = PdfReader(f)
        for page in reader.pages:
            parsed_data += page.extract_text()

        return parsed_data

    def _get_partner_from_response(self, response_dict,create_partner ):
        partner_dict = response_dict.get('partner', {})
        name = partner_dict.get('name')
        vat = partner_dict.get('vat_id')
        email = partner_dict.get('email')
        email = email.strip() if email else None

        if email:
            user_emails = [x.email.strip() for x in self.env['res.users'].search([]) if x.email]
            # add the com[any mails
            company_mail = self.env.company.email.strip() if self.env.company.email else False
            if company_mail:
                user_emails.append(self.env.company.email.strip())
            if email not in user_emails:
                email = False

        # Build domain for searching
        domain = [('name', '=', name)] if name else \
            [('email', '=', email)] if email else \
                [('vat', '=', vat)] if vat else []
        # Search for partner using the domain
        partner_id = self.env['res.partner'].search(domain, limit=1)
        # If multiple conditions are provided, refine the search
        if len(partner_id) > 1:
            refined_domain = domain + [('vat', '=', vat)] if vat else domain
            partner_id = self.env['res.partner'].search(refined_domain, limit=1)
        if not partner_id:
            all_partner_ids = self.env['res.partner'].search([])
            threshold_similarity = 80
            filtered_partner = [
                partner for partner in all_partner_ids
                if fuzz.ratio(name, partner.name) >= threshold_similarity
            ]
            if filtered_partner:
                # Si hay al menos una coincidencia que cumple con el umbral, toma la primera como mejor coincidencia
                partner_id = filtered_partner[0]

        if not partner_id and create_partner and name:
            partner_id = self.env['res.partner'].create({
                'name': name,
                'vat': vat if vat else False,
                'email': email if email else False
            })
        return partner_id

    def _fix_json(self, json_data):
        system = """JSON Fixing Tool: Correct JSON Errors Given a JSON string with mistakes causing """ + \
                 """JSONDecodeError, fix it and respond with a valid JSON. Ensure compliance with RFC8259 """ + \
                 """standards, checking for issues like trailing commas, special characters, and extra """ + \
                 """characters. Do not add explanations or ``` tags. Only provide a correctly formatted JSON object.
                 """
        conversation_history = [{'role': 'system', 'content': system}]
        return self.generate_text_olg_api(json_data, conversation_history)
