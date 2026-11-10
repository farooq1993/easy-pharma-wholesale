GST_STATE_CODES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman and Diu",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
}
GST_STATE_CHOICES = tuple(GST_STATE_CODES.items())


def gst_state_code(gstin=None, state_name=None, state_code=None):
    """Return a GST state code from a GSTIN or a known state name."""
    normalized_gstin = (gstin or "").strip().upper()
    if len(normalized_gstin) == 15 and normalized_gstin[:2].isdigit():
        return normalized_gstin[:2]

    normalized_code = (state_code or "").strip()
    if normalized_code in GST_STATE_CODES:
        return normalized_code

    normalized_name = " ".join((state_name or "").casefold().replace("&", "and").split())
    if not normalized_name:
        return None

    for code, name in GST_STATE_CODES.items():
        if normalized_name == " ".join(name.casefold().replace("&", "and").split()):
            return code

    aliases = {
        "orissa": "21",
        "pondicherry": "34",
        "jammu and kashmir": "01",
        "dadra and nagar haveli": "26",
        "daman and diu": "26",
    }
    return aliases.get(normalized_name)


def split_gst_amount(gst_amount, supplier_state_code, recipient_state_code):
    """Return tax components; leave them unclassified when place of supply is unknown."""
    if not supplier_state_code or not recipient_state_code:
        zero = gst_amount * 0
        return {"cgst": zero, "sgst": zero, "igst": zero, "unclassified": gst_amount, "classified": False}
    if supplier_state_code == recipient_state_code:
        half_tax = gst_amount / 2
        return {"cgst": half_tax, "sgst": half_tax, "igst": gst_amount * 0, "unclassified": gst_amount * 0, "classified": True}
    zero = gst_amount * 0
    return {"cgst": zero, "sgst": zero, "igst": gst_amount, "unclassified": zero, "classified": True}
