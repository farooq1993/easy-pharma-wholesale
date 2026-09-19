import base64
import time
import requests
import json
import re
import os
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', default='')

def extract_purchase_bill_data(image_file):
    """
    Sends the purchase bill/invoice image to Gemini API to extract details.
    image_file: file-like object or bytes
    """
    api_key = os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
    if api_key:
        api_key = api_key.split('#')[0].strip().split()[0]
    
    # Read image bytes
    if hasattr(image_file, 'read'):
        image_data = image_file.read()
    else:
        image_data = image_file

    if not api_key or len(api_key) < 10:
        # Fallback parser if GEMINI_API_KEY is not configured
        return None

    base64_image = base64.b64encode(image_data).decode('utf-8')

    prompt = (
        "You are an expert accountant and pharmacy billing OCR AI specializing in Indian pharmacy purchase bills/invoices.\n"
        "Carefully parse this purchase bill image and extract all details with extreme precision:\n\n"
        "1. Supplier/Vendor name (distributor/wholesaler selling the medicines)\n"
        "2. Invoice number (bill number or reference number)\n"
        "3. Purchase/Invoice date (YYYY-MM-DD format if visible, or original text date converted to standard date)\n"
        "4. Payment mode ('Cash' or 'Credit' if visible, default to 'Credit')\n"
        "5. Line items (medicines/products table). For each item on EVERY row:\n"
        "   - name: Medicine or product name with brand & strength/dosage (e.g. 'Pantocid 40mg', 'Augmentin 625 Duo', 'Telma 40'). Remove leading serial numbers (e.g., '1.', '2.') or stray symbols.\n"
        "   - batch_number: Exact batch number on this specific line (e.g. 'B2401', 'DFPL701', 'EF9T705').\n"
        "     * CRITICAL FOR BATCH: Maintain strict 1-to-1 horizontal row alignment. Each batch must match ONLY its corresponding row item. Do NOT shift batch numbers across adjacent rows.\n"
        "   - expiry_date: Expiry date (convert to MM/YY format e.g. '05/27', '11/27', '06/2027'). Expiry represents future dates.\n"
        "   - quantity: Exact billed/purchased quantity.\n"
        "     * CRITICAL FOR QUANTITY: Read every single digit with extreme care. NEVER truncate or drop digits (e.g., if quantity is '240', extract exactly 240, NOT 24).\n"
        "   - free_quantity: Free/scheme quantity received (e.g. 0, 1, 2. Default to 0 if none).\n"
        "   - purchase_price: Purchase rate/price per unit/pack excluding GST tax (or P.T.S / billing rate).\n"
        "   - mrp: Maximum Retail Price (MRP) per pack/box/strip.\n"
        "   - tax_percentage: GST tax rate percentage (e.g. 5, 12, 18. Default to 5 or 12 if not stated).\n"
        "   - total: Net line amount for this row (quantity * purchase_price, or bill line amount).\n\n"
        "Output MUST be a valid JSON object matching this schema:\n"
        "{\n"
        "  \"supplier_name\": \"string or null\",\n"
        "  \"invoice_number\": \"string or null\",\n"
        "  \"purchase_date\": \"string format YYYY-MM-DD or null\",\n"
        "  \"payment_mode\": \"Cash or Credit\",\n"
        "  \"items\": [\n"
        "    {\n"
        "      \"name\": \"string\",\n"
        "      \"batch_number\": \"string or null\",\n"
        "      \"expiry_date\": \"string format MM/YY or YYYY-MM-DD or null\",\n"
        "      \"quantity\": integer,\n"
        "      \"free_quantity\": integer,\n"
        "      \"purchase_price\": float,\n"
        "      \"mrp\": float,\n"
        "      \"tax_percentage\": float,\n"
        "      \"total\": float\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Return ONLY the raw JSON block without markdown formatting or code blocks."
    )

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash"
    ]

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1
        }
    }

    last_error = None
    response = None

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        max_retries = 2
        for attempt in range(max_retries):
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    response = res
                    break
                elif res.status_code in [429, 503] and attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                else:
                    last_error = f"{model_name} status {res.status_code}"
                    break
            except Exception as e:
                last_error = f"{model_name} exception: {str(e)}"
                break
        if response and response.status_code == 200:
            break

    if not response or response.status_code != 200:
        return None

    resp_json = response.json()
    try:
        raw_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_text = raw_text.strip()
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_text, re.DOTALL)
        if match:
            cleaned_text = match.group(1)
        parsed_data = json.loads(cleaned_text.strip())
        return parsed_data
    except Exception:
        return None
