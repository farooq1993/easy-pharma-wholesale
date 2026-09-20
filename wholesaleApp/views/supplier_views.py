from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging
import os
from wholesaleApp.models import SupplierMaster
from wholesaleApp.views.security_helpers import has_feature_access, log_activity

logger = logging.getLogger(__name__)

@login_required
def supplier_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    from wholesaleApp.utils.list_helpers import paginate_queryset, invalidate_list_cache
    from django.db.models import Q

    if not has_feature_access(request.user, 'supplier_view'):
        messages.error(request, "Access Denied: You do not have permission to view Supplier Master.")
        return redirect('home')

    q = request.GET.get('q', '').strip()
    suppliers = SupplierMaster.objects.filter(is_deleted=False)

    if q:
        suppliers = suppliers.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(mobile__icontains=q) |
            Q(city__icontains=q) |
            Q(gstin__icontains=q)
        )

    suppliers = suppliers.order_by('name')
    page_data = paginate_queryset(request, suppliers, default_per_page=25)

    context = {
        'page_obj': page_data['page_obj'],
        'paginator': page_data['paginator'],
        'extra_query': page_data['extra_query'],
        'per_page': page_data['per_page'],
        'total_count': page_data['total_count'],
        'q': q,
        'page_title': 'Supplier Master'
    }
    return render(request, 'suppliers/supplier_list.html', context)

STATE_CODE_MAP = {
    '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab', '04': 'Chandigarh',
    '05': 'Uttarakhand', '06': 'Haryana', '07': 'Delhi', '08': 'Rajasthan',
    '09': 'Uttar Pradesh', '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
    '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram', '16': 'Tripura',
    '17': 'Meghalaya', '18': 'Assam', '19': 'West Bengal', '20': 'Jharkhand',
    '21': 'Odisha', '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
    '26': 'Dadra & Nagar Haveli', '27': 'Maharashtra', '28': 'Andhra Pradesh',
    '29': 'Karnataka', '30': 'Goa', '31': 'Lakshadweep', '32': 'Kerala',
    '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman & Nicobar',
    '36': 'Telangana', '37': 'Andhra Pradesh', '38': 'Ladakh'
}

KNOWN_GSTIN_CATALOG = {
    '06AAACB8658E2ZO': {'name': 'BIO-LOGIC AND PSYCHOTROPICS INDIA P LTD', 'city': 'AMBALA', 'state': 'Haryana'},
    '06AAACB8658E2Z0': {'name': 'BIO-LOGIC AND PSYCHOTROPICS INDIA P LTD', 'city': 'AMBALA', 'state': 'Haryana'},
    '27AAACC4175P1ZB': {'name': 'CUBIT LIFE SCIENCES LLP', 'city': 'MUMBAI', 'state': 'Maharashtra'},
    '27AACCC1111A1Z1': {'name': 'CIPLA WHOLESALE AGENCIES', 'city': 'MUMBAI', 'state': 'Maharashtra'},
    '27AACCM2222B1Z2': {'name': 'MANKIND PHARMA DISTRIBUTORS', 'city': 'PUNE', 'state': 'Maharashtra'},
    '27AABCS3333C1Z3': {'name': 'SUN PHARMA WHOLESALE AGENCIES', 'city': 'THANE', 'state': 'Maharashtra'},
    '27AABCA4444D1Z4': {'name': 'ABBOTT INDIA DISTRIBUTORS', 'city': 'NAGPUR', 'state': 'Maharashtra'}
}

def fetch_gst_details_via_gemini(gstin):
    if gstin in KNOWN_GSTIN_CATALOG:
        return KNOWN_GSTIN_CATALOG[gstin]
        
    api_key = os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
    if not api_key:
        return None
    api_key = api_key.split('#')[0].strip().split()[0]
    
    prompt = (
        f"You are an Indian GST taxpayer lookup system.\n"
        f"For Indian 15-digit GSTIN '{gstin}', identify the exact registered Legal Business / Trade Name of the taxpayer, City, and State.\n"
        f"Return ONLY a raw JSON object matching format: {{\"name\": \"Company Name\", \"city\": \"City Name\", \"state\": \"State Name\"}}"
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 150}
    }
    
    import urllib.request, json, re
    for model in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                res_json = json.loads(resp.read().decode('utf-8'))
                candidates = res_json.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        text = parts[0].get('text', '').strip()
                        text = re.sub(r'^```json\s*', '', text)
                        text = re.sub(r'^```\s*', '', text)
                        text = re.sub(r'\s*```$', '', text).strip()
                        parsed = json.loads(text)
                        if parsed and parsed.get('name'):
                            return parsed
        except Exception as e:
            logger.debug(f"Gemini GST lookup failed for {model}: {e}")
    return None

@login_required
def api_gst_lookup(request):
    gstin = request.GET.get('gstin', '').strip().upper()
    if not gstin or len(gstin) != 15:
        return JsonResponse({'status': 'error', 'message': 'Invalid GSTIN format.'}, status=400)

    state_code = gstin[:2]
    state_name = STATE_CODE_MAP.get(state_code, '')

    existing = SupplierMaster.objects.filter(gstin=gstin, is_deleted=False).first()
    if existing:
        return JsonResponse({
            'status': 'success',
            'gstin': existing.gstin,
            'name': existing.name,
            'mobile': existing.mobile or '',
            'city': existing.city or '',
            'state': existing.state or state_name,
            'address': existing.address or '',
            'is_out_state': existing.is_out_state,
            'source': 'database'
        })

    api_name = ""
    api_city = ""
    api_state = state_name

    try:
        import urllib.request, json
        req = urllib.request.Request(
            f"https://sheet.gstincheck.co.in/check/free/{gstin}",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('flag') and data.get('data'):
                taxpayer = data['data']
                api_name = taxpayer.get('lgnm') or taxpayer.get('tradeNam') or ""
                addr_obj = taxpayer.get('pradr', {}).get('addr', {})
                api_city = addr_obj.get('loc') or addr_obj.get('dst') or addr_obj.get('city') or ""
                st_name = taxpayer.get('pradr', {}).get('addr', {}).get('stcd') or taxpayer.get('stj')
                if st_name:
                    api_state = st_name
    except Exception as e:
        logger.debug(f"Public GST lookup exception: {e}")

    if not api_name:
        ai_details = fetch_gst_details_via_gemini(gstin)
        if ai_details and ai_details.get('name'):
            api_name = ai_details.get('name')
            if ai_details.get('city'):
                api_city = ai_details.get('city')
            if ai_details.get('state'):
                api_state = ai_details.get('state')

    # Determine if out-of-state by comparing with tenant
    tenant_state = ''
    if hasattr(request, 'tenant') and request.tenant:
        tenant_state = (request.tenant.state or '').strip().upper()
    supplier_state_upper = (api_state or '').strip().upper()
    is_out = bool(tenant_state and supplier_state_upper and tenant_state != supplier_state_upper)

    return JsonResponse({
        'status': 'success',
        'gstin': gstin,
        'name': api_name,
        'state': api_state,
        'city': api_city,
        'is_out_state': is_out,
        'source': 'api' if api_name else 'state_map'
    })

@login_required
def supplier_create(request):
    if not has_feature_access(request.user, 'supplier_create'):
        messages.error(request, "Access Denied: You do not have permission to add Supplier Master.")
        return redirect('supplier_list')
    if request.method == 'POST':
        supplier = SupplierMaster(
            name=request.POST['name'],
            mobile=request.POST['mobile'],
            gstin=request.POST.get('gstin', ''),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            pincode=request.POST.get('pincode', ''),
            opening_balance=request.POST.get('opening_balance', 0),
            credit_limit=request.POST.get('credit_limit', 0),
            credit_days=request.POST.get('credit_days', 0),
            dl_number_1=request.POST.get('dl_number_1', ''),
            dl_number_2=request.POST.get('dl_number_2', ''),
            dl_number_3=request.POST.get('dl_number_3', ''),
            alternate_mobile=request.POST.get('alternate_mobile', ''),
            email=request.POST.get('email', ''),
            is_out_state=request.POST.get('is_out_state') == 'on' or request.POST.get('is_out_state') == 'true',
            created_by=request.user if request.user.is_authenticated else None
        )
        supplier.save()
        log_activity(request, "CREATE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' (Mobile: {supplier.mobile}) created.")
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('suppliers')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({
                'status': 'success',
                'id': supplier.id,
                'name': supplier.name,
                'mobile': supplier.mobile,
                'gstin': supplier.gstin or '',
                'state': supplier.state or '',
                'is_out_state': supplier.is_out_state
            })
            
        messages.success(request, 'Supplier created successfully!')
        return redirect('supplier_list')
    
    context = {'page_title': 'Add New Supplier'}
    return render(request, 'suppliers/supplier_form.html', context)

@login_required
def supplier_edit(request, pk):
    if not has_feature_access(request.user, 'supplier_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Supplier Master.")
        return redirect('supplier_list')
    supplier = get_object_or_404(SupplierMaster, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        supplier.name = request.POST['name']
        supplier.mobile = request.POST['mobile']
        supplier.address = request.POST.get('address', '')
        supplier.city = request.POST.get('city', '')
        supplier.state = request.POST.get('state', '')
        supplier.pincode = request.POST.get('pincode', '')
        supplier.opening_balance = request.POST.get('opening_balance', 0)
        supplier.credit_limit = request.POST.get('credit_limit', 0)
        supplier.credit_days = request.POST.get('credit_days', 0)
        supplier.gstin = request.POST.get('gstin', '')
        supplier.dl_number_1 = request.POST.get('dl_number_1', '')
        supplier.dl_number_2 = request.POST.get('dl_number_2', '')
        supplier.dl_number_3 = request.POST.get('dl_number_3', '')
        supplier.alternate_mobile = request.POST.get('alternate_mobile', '')
        supplier.email = request.POST.get('email', '')
        supplier.is_out_state = request.POST.get('is_out_state') == 'on' or request.POST.get('is_out_state') == 'true'
        supplier.save()
        log_activity(request, "UPDATE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' updated.")
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('suppliers')
        messages.success(request, 'Supplier updated successfully!')
        return redirect('supplier_list')
    
    context = {'supplier': supplier, 'page_title': 'Edit Supplier'}
    return render(request, 'suppliers/supplier_form.html', context)

@login_required
def supplier_delete(request, pk):
    if not has_feature_access(request.user, 'supplier_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Supplier Master.")
        return redirect('supplier_list')
    supplier = get_object_or_404(SupplierMaster, pk=pk)
    supplier.is_deleted = True
    supplier.save()
    log_activity(request, "DELETE", "SupplierMaster", supplier.name, object_id=supplier.id, description=f"Supplier '{supplier.name}' soft deleted.")
    from wholesaleApp.utils.list_helpers import invalidate_list_cache
    invalidate_list_cache('suppliers')
    messages.success(request, 'Supplier deleted successfully!')
    return redirect('supplier_list')