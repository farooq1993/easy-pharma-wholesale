from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging
from wholesaleApp.models import CompanyMaster, DrugMaster, ProductTypeMaster, ProductMaster, TaxMaster, ScheduleMaster
from wholesaleApp.views.security_helpers import has_feature_access, log_activity

logger = logging.getLogger(__name__)


def ensure_default_tax_and_schedules():
    """Ensure standard GST slabs and pharma drug schedules exist."""
    try:
        if not TaxMaster.objects.filter(is_deleted=False).exists():
            default_taxes = [
                {"name": "0% (Exempted)", "rate": 0.00, "cgst_rate": 0.00, "sgst_rate": 0.00, "igst_rate": 0.00, "is_default": False},
                {"name": "5% (Life Saving / Essentials)", "rate": 5.00, "cgst_rate": 2.50, "sgst_rate": 2.50, "igst_rate": 5.00, "is_default": False},
                {"name": "12% (Standard Pharma)", "rate": 12.00, "cgst_rate": 6.00, "sgst_rate": 6.00, "igst_rate": 12.00, "is_default": True},
                {"name": "18% (Healthcare / FMCG)", "rate": 18.00, "cgst_rate": 9.00, "sgst_rate": 9.00, "igst_rate": 18.00, "is_default": False},
                {"name": "28% (Cosmetics / Luxury)", "rate": 28.00, "cgst_rate": 14.00, "sgst_rate": 14.00, "igst_rate": 28.00, "is_default": False},
            ]
            for t in default_taxes:
                TaxMaster.objects.create(**t)

        if not ScheduleMaster.objects.filter(is_deleted=False).exists():
            default_schedules = [
                {"name": "Schedule H", "code": "H", "warning_text": "Warning: To be sold by retail on the prescription of a Registered Medical Practitioner only.", "requires_prescription": True},
                {"name": "Schedule H1", "code": "H1", "warning_text": "Warning: It is dangerous to take this preparation except in accordance with medical advice. Not to be sold by retail without prescription.", "requires_prescription": True},
                {"name": "Schedule X", "code": "X", "warning_text": "Warning: Schedule X Drug - Narcotic/Psychotropic. Strict prescription and record maintenance required.", "requires_prescription": True},
                {"name": "Schedule G", "code": "G", "warning_text": "Caution: It is dangerous to take this preparation except under medical supervision.", "requires_prescription": True},
                {"name": "OTC (Over The Counter)", "code": "OTC", "warning_text": "Non-prescription General Sales item.", "requires_prescription": False},
                {"name": "Narcotics / NDPS", "code": "NDPS", "warning_text": "Strict NDPS regulations apply.", "requires_prescription": True},
            ]
            for s in default_schedules:
                ScheduleMaster.objects.create(**s)
    except Exception as e:
        logger.warning(f"Error checking default tax/schedule masters: {e}")

# ==================== COMPANY MASTER VIEWS ====================
@login_required
def company_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    from wholesaleApp.utils.list_helpers import paginate_queryset, invalidate_list_cache
    from django.db.models import Q

    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Company Master.")
        return redirect('home')

    q = request.GET.get('q', '').strip()
    companies = CompanyMaster.objects.filter(is_deleted=False)

    if q:
        companies = companies.filter(
            Q(name__icontains=q) |
            Q(code__icontains=q)
        )

    companies = companies.order_by('name')
    page_data = paginate_queryset(request, companies, default_per_page=25)

    context = {
        'page_obj': page_data['page_obj'],
        'paginator': page_data['paginator'],
        'extra_query': page_data['extra_query'],
        'per_page': page_data['per_page'],
        'total_count': page_data['total_count'],
        'q': q,
        'page_title': 'Company Master'
    }
    return render(request, 'companies/company_list.html', context)

@login_required
def company_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Company Master.")
        return redirect('company_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', '')
        
        if CompanyMaster.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"Company '{name}' already exists.")
        else:
            company = CompanyMaster(
                name=name,
                code=code,
                created_by=request.user if request.user.is_authenticated else None
            )
            company.save()
            log_activity(request, "CREATE", "CompanyMaster", company.name, object_id=company.id, description=f"Company '{name}' created.")
            from wholesaleApp.utils.list_helpers import invalidate_list_cache
            invalidate_list_cache('companies')
            messages.success(request, 'Company created successfully!')
            return redirect('company_list')
            
    context = {'page_title': 'Add New Company'}
    return render(request, 'companies/company_form.html', context)

@login_required
def company_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Company Master.")
        return redirect('company_list')
    company = get_object_or_404(CompanyMaster, pk=pk, is_deleted=False)
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', '')
        
        if CompanyMaster.objects.filter(name__iexact=name, is_deleted=False).exclude(pk=pk).exists():
            messages.error(request, f"Company '{name}' already exists.")
        else:
            company.name = name
            company.code = code
            company.save()
            log_activity(request, "UPDATE", "CompanyMaster", company.name, object_id=company.id, description=f"Company '{name}' updated.")
            from wholesaleApp.utils.list_helpers import invalidate_list_cache
            invalidate_list_cache('companies')
            messages.success(request, 'Company updated successfully!')
            return redirect('company_list')
            
    context = {'company': company, 'page_title': 'Edit Company'}
    return render(request, 'companies/company_form.html', context)

@login_required
def company_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Company Master.")
        return redirect('company_list')
    company = get_object_or_404(CompanyMaster, pk=pk)
    company.is_deleted = True
    company.save()
    log_activity(request, "DELETE", "CompanyMaster", company.name, object_id=company.id, description=f"Company '{company.name}' soft deleted.")
    from wholesaleApp.utils.list_helpers import invalidate_list_cache
    invalidate_list_cache('companies')
    messages.success(request, 'Company deleted successfully!')
    return redirect('company_list')


# ==================== DRUG MASTER VIEWS ====================
@login_required
def drug_list(request):
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Drug Compositions.")
        return redirect('home')
    drugs = DrugMaster.objects.filter(is_deleted=False)
    context = {
        'drugs': drugs,
        'page_title': 'Drug Composition Master'
    }
    return render(request, 'drugs/drug_list.html', context)

@login_required
def drug_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Drug Compositions.")
        return redirect('drug_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        if DrugMaster.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"Composition '{name}' already exists.")
        else:
            drug = DrugMaster(
                name=name,
                created_by=request.user if request.user.is_authenticated else None
            )
            drug.save()
            log_activity(request, "CREATE", "DrugMaster", drug.name, object_id=drug.id, description=f"Drug composition '{name}' created.")
            messages.success(request, 'Drug composition created successfully!')
            return redirect('drug_list')
            
    context = {'page_title': 'Add New Generic Composition'}
    return render(request, 'drugs/drug_form.html', context)

@login_required
def drug_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Drug Compositions.")
        return redirect('drug_list')
    drug = get_object_or_404(DrugMaster, pk=pk, is_deleted=False)
    if request.method == 'POST':
        name = request.POST.get('name')
        if DrugMaster.objects.filter(name__iexact=name, is_deleted=False).exclude(pk=pk).exists():
            messages.error(request, f"Composition '{name}' already exists.")
        else:
            drug.name = name
            drug.save()
            log_activity(request, "UPDATE", "DrugMaster", drug.name, object_id=drug.id, description=f"Drug composition '{name}' updated.")
            messages.success(request, 'Drug composition updated successfully!')
            return redirect('drug_list')
            
    context = {'drug': drug, 'page_title': 'Edit Generic Composition'}
    return render(request, 'drugs/drug_form.html', context)

@login_required
def drug_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Drug Compositions.")
        return redirect('drug_list')
    drug = get_object_or_404(DrugMaster, pk=pk)
    drug.is_deleted = True
    drug.save()
    log_activity(request, "DELETE", "DrugMaster", drug.name, object_id=drug.id, description=f"Drug composition '{drug.name}' soft deleted.")
    messages.success(request, 'Drug composition deleted successfully!')
    return redirect('drug_list')


# ==================== PRODUCT TYPE MASTER VIEWS ====================
@login_required
def type_list(request):
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Product Types.")
        return redirect('home')
    types = ProductTypeMaster.objects.filter(is_deleted=False)
    context = {
        'types': types,
        'page_title': 'Product Type Master'
    }
    return render(request, 'product_types/type_list.html', context)

@login_required
def type_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Product Types.")
        return redirect('type_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        if ProductTypeMaster.objects.filter(name__iexact=name, is_deleted=False).exists():
            messages.error(request, f"Product Type '{name}' already exists.")
        else:
            p_type = ProductTypeMaster(
                name=name,
                created_by=request.user if request.user.is_authenticated else None
            )
            p_type.save()
            log_activity(request, "CREATE", "ProductTypeMaster", p_type.name, object_id=p_type.id, description=f"Product type '{name}' created.")
            messages.success(request, 'Product Type created successfully!')
            return redirect('type_list')
            
    context = {'page_title': 'Add New Product Type / Form'}
    return render(request, 'product_types/type_form.html', context)

@login_required
def type_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Product Types.")
        return redirect('type_list')
    p_type = get_object_or_404(ProductTypeMaster, pk=pk, is_deleted=False)
    if request.method == 'POST':
        name = request.POST.get('name')
        if ProductTypeMaster.objects.filter(name__iexact=name, is_deleted=False).exclude(pk=pk).exists():
            messages.error(request, f"Product Type '{name}' already exists.")
        else:
            p_type.name = name
            p_type.save()
            log_activity(request, "UPDATE", "ProductTypeMaster", p_type.name, object_id=p_type.id, description=f"Product type '{name}' updated.")
            messages.success(request, 'Product Type updated successfully!')
            return redirect('type_list')
            
    context = {'p_type': p_type, 'page_title': 'Edit Product Type'}
    return render(request, 'product_types/type_form.html', context)

@login_required
def type_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Product Types.")
        return redirect('type_list')
    p_type = get_object_or_404(ProductTypeMaster, pk=pk)
    p_type.is_deleted = True
    p_type.save()
    log_activity(request, "DELETE", "ProductTypeMaster", p_type.name, object_id=p_type.id, description=f"Product type '{p_type.name}' soft deleted.")
    messages.success(request, 'Product Type deleted successfully!')
    return redirect('type_list')


# ==================== PRODUCT MASTER (ITEM MASTER) VIEWS ====================
@login_required
def product_list(request):
    from wholesaleApp.views.security_helpers import has_feature_access
    from wholesaleApp.utils.list_helpers import paginate_queryset, invalidate_list_cache
    from django.db.models import Q

    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Products.")
        return redirect('home')

    q = request.GET.get('q', '').strip()
    company_id = request.GET.get('company', '').strip()
    type_id = request.GET.get('type', '').strip()

    products = ProductMaster.objects.filter(is_deleted=False).select_related('company', 'drug_composition', 'product_type')

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(hsn_code__icontains=q) |
            Q(pack_size__icontains=q)
        )

    if company_id and company_id.isdigit():
        products = products.filter(company_id=int(company_id))

    if type_id and type_id.isdigit():
        products = products.filter(product_type_id=int(type_id))

    products = products.order_by('name')
    page_data = paginate_queryset(request, products, default_per_page=25)

    filter_companies = CompanyMaster.objects.filter(is_deleted=False).order_by('name')
    filter_types = ProductTypeMaster.objects.filter(is_deleted=False).order_by('name')

    context = {
        'page_obj': page_data['page_obj'],
        'paginator': page_data['paginator'],
        'extra_query': page_data['extra_query'],
        'per_page': page_data['per_page'],
        'total_count': page_data['total_count'],
        'filter_companies': filter_companies,
        'filter_types': filter_types,
        'q': q,
        'company_id': company_id,
        'type_id': type_id,
        'page_title': 'Product Master (Item Catalog)'
    }
    return render(request, 'products/product_list.html', context)

@login_required
def product_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Products.")
        return redirect('product_list')
    ensure_default_tax_and_schedules()
    companies = CompanyMaster.objects.filter(status=True, is_deleted=False)
    drugs = DrugMaster.objects.filter(status=True, is_deleted=False)
    types = ProductTypeMaster.objects.filter(status=True, is_deleted=False)
    tax_slabs = TaxMaster.objects.filter(status=True, is_deleted=False).order_by('rate')
    schedules = ScheduleMaster.objects.filter(status=True, is_deleted=False).order_by('name')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        company_id = request.POST.get('company')
        drug_id = request.POST.get('drug_composition')
        type_id = request.POST.get('product_type')
        tax_slab_id = request.POST.get('tax_slab')
        schedule_id = request.POST.get('schedule')
        pack_size = request.POST.get('pack_size')
        hsn_code = request.POST.get('hsn_code', '')
        gst_rate = request.POST.get('gst_rate', 12.00)
        min_stock = request.POST.get('min_stock', 10)
        scheme_qty = request.POST.get('scheme_qty', 0)
        scheme_free = request.POST.get('scheme_free', 0)
        
        # Calculate gst_rate from selected slab if available
        if tax_slab_id and tax_slab_id.isdigit():
            slab = TaxMaster.objects.filter(id=int(tax_slab_id), is_deleted=False).first()
            if slab:
                gst_rate = slab.rate
        
        product = ProductMaster(
            name=name,
            company_id=company_id,
            drug_composition_id=drug_id if drug_id else None,
            product_type_id=type_id,
            tax_slab_id=tax_slab_id if (tax_slab_id and tax_slab_id.isdigit()) else None,
            schedule_id=schedule_id if (schedule_id and schedule_id.isdigit()) else None,
            pack_size=pack_size,
            hsn_code=hsn_code,
            gst_rate=gst_rate,
            min_stock=min_stock,
            scheme_qty=scheme_qty if scheme_qty else 0,
            scheme_free=scheme_free if scheme_free else 0,
            created_by=request.user if request.user.is_authenticated else None
        )
        product.save()
        log_activity(request, "CREATE", "ProductMaster", product.name, object_id=product.id, description=f"Product '{name}' (Pack: {pack_size}, HSN: {hsn_code}, GST: {gst_rate}%) created.")
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('products')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({
                'status': 'success',
                'id': product.id,
                'name': product.name,
                'pack_size': product.pack_size,
                'gst_rate': float(product.gst_rate)
            })
            
        messages.success(request, 'Product created successfully!')
        return redirect('product_list')
        
    context = {
        'companies': companies,
        'drugs': drugs,
        'types': types,
        'tax_slabs': tax_slabs,
        'schedules': schedules,
        'page_title': 'Add New Product (Item)'
    }
    return render(request, 'products/product_form.html', context)

@login_required
def product_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({'status': 'error', 'message': 'Access Denied: You do not have permission to edit Products.'}, status=403)
        messages.error(request, "Access Denied: You do not have permission to edit Products.")
        return redirect('product_list')
    ensure_default_tax_and_schedules()
    product = get_object_or_404(ProductMaster, pk=pk, is_deleted=False)
    companies = CompanyMaster.objects.filter(status=True, is_deleted=False)
    drugs = DrugMaster.objects.filter(status=True, is_deleted=False)
    types = ProductTypeMaster.objects.filter(status=True, is_deleted=False)
    tax_slabs = TaxMaster.objects.filter(status=True, is_deleted=False).order_by('rate')
    schedules = ScheduleMaster.objects.filter(status=True, is_deleted=False).order_by('name')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            product.name = name
        company_id = request.POST.get('company')
        if company_id:
            product.company_id = company_id
        drug_id = request.POST.get('drug_composition')
        if drug_id is not None:
            product.drug_composition_id = drug_id if drug_id else None
        type_id = request.POST.get('product_type')
        if type_id:
            product.product_type_id = type_id
        
        tax_slab_id = request.POST.get('tax_slab')
        if tax_slab_id is not None:
            if tax_slab_id and tax_slab_id.isdigit():
                product.tax_slab_id = int(tax_slab_id)
                slab = TaxMaster.objects.filter(id=int(tax_slab_id), is_deleted=False).first()
                if slab:
                    product.gst_rate = slab.rate
            else:
                product.tax_slab = None
                
        schedule_id = request.POST.get('schedule')
        if schedule_id is not None:
            product.schedule_id = int(schedule_id) if (schedule_id and schedule_id.isdigit()) else None

        pack_size = request.POST.get('pack_size')
        if pack_size:
            product.pack_size = pack_size
        if 'hsn_code' in request.POST:
            product.hsn_code = request.POST.get('hsn_code', '')
        if 'gst_rate' in request.POST and not product.tax_slab:
            product.gst_rate = request.POST.get('gst_rate', 12.00)
        if 'min_stock' in request.POST and request.POST.get('min_stock'):
            product.min_stock = request.POST.get('min_stock')
        product.save()
        log_activity(request, "UPDATE", "ProductMaster", product.name, object_id=product.id, description=f"Product '{product.name}' updated.")
        from wholesaleApp.utils.list_helpers import invalidate_list_cache
        invalidate_list_cache('products')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
            return JsonResponse({
                'status': 'success',
                'id': product.id,
                'name': product.name,
                'pack_size': product.pack_size,
                'gst_rate': float(product.gst_rate),
                'company_id': product.company_id,
                'product_type_id': product.product_type_id,
                'hsn_code': product.hsn_code
            })

        messages.success(request, 'Product updated successfully!')
        return redirect('product_list')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('json') == 'true':
        return JsonResponse({
            'status': 'success',
            'id': product.id,
            'name': product.name,
            'pack_size': product.pack_size,
            'gst_rate': float(product.gst_rate),
            'company_id': product.company_id,
            'product_type_id': product.product_type_id,
            'hsn_code': product.hsn_code,
            'min_stock': product.min_stock
        })
        
    context = {
        'product': product,
        'companies': companies,
        'drugs': drugs,
        'types': types,
        'tax_slabs': tax_slabs,
        'schedules': schedules,
        'page_title': 'Edit Product'
    }
    return render(request, 'products/product_form.html', context)

@login_required
def product_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Products.")
        return redirect('product_list')
    product = get_object_or_404(ProductMaster, pk=pk)
    product.is_deleted = True
    product.save()
    log_activity(request, "DELETE", "ProductMaster", product.name, object_id=product.id, description=f"Product '{product.name}' soft deleted.")
    from wholesaleApp.utils.list_helpers import invalidate_list_cache
    invalidate_list_cache('products')
    messages.success(request, 'Product deleted successfully!')
    return redirect('product_list')


# ==================== TAX MASTER (GST SLABS) VIEWS ====================
@login_required
def tax_list(request):
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Tax Master.")
        return redirect('home')
    ensure_default_tax_and_schedules()
    taxes = TaxMaster.objects.filter(is_deleted=False).order_by('rate')
    context = {
        'taxes': taxes,
        'page_title': 'Tax Master (GST Slabs)'
    }
    return render(request, 'tax_master/tax_list.html', context)

@login_required
def tax_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Tax Slabs.")
        return redirect('tax_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        rate = request.POST.get('rate')
        cgst_rate = request.POST.get('cgst_rate')
        sgst_rate = request.POST.get('sgst_rate')
        igst_rate = request.POST.get('igst_rate')
        is_default = request.POST.get('is_default') == 'on' or request.POST.get('is_default') == 'true'
        description = request.POST.get('description', '')

        try:
            rate_val = float(rate)
            tax = TaxMaster(
                name=name,
                rate=rate_val,
                cgst_rate=float(cgst_rate) if cgst_rate else round(rate_val / 2, 2),
                sgst_rate=float(sgst_rate) if sgst_rate else round(rate_val / 2, 2),
                igst_rate=float(igst_rate) if igst_rate else rate_val,
                is_default=is_default,
                description=description,
                created_by=request.user if request.user.is_authenticated else None
            )
            if is_default:
                TaxMaster.objects.filter(is_deleted=False).update(is_default=False)
            tax.save()
            log_activity(request, "CREATE", "TaxMaster", tax.name, object_id=tax.id, description=f"Tax Slab '{name}' ({rate_val}%) created.")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'id': tax.id, 'name': tax.name, 'rate': float(tax.rate)})
            
            messages.success(request, f"Tax slab '{name}' created successfully!")
            return redirect('tax_list')
        except Exception as e:
            messages.error(request, f"Error creating tax slab: {str(e)}")

    context = {'page_title': 'Add New Tax Slab (GST)'}
    return render(request, 'tax_master/tax_form.html', context)

@login_required
def tax_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Tax Slabs.")
        return redirect('tax_list')
    tax = get_object_or_404(TaxMaster, pk=pk, is_deleted=False)
    if request.method == 'POST':
        name = request.POST.get('name')
        rate = request.POST.get('rate')
        cgst_rate = request.POST.get('cgst_rate')
        sgst_rate = request.POST.get('sgst_rate')
        igst_rate = request.POST.get('igst_rate')
        is_default = request.POST.get('is_default') == 'on' or request.POST.get('is_default') == 'true'
        description = request.POST.get('description', '')

        try:
            rate_val = float(rate)
            tax.name = name
            tax.rate = rate_val
            tax.cgst_rate = float(cgst_rate) if cgst_rate else round(rate_val / 2, 2)
            tax.sgst_rate = float(sgst_rate) if sgst_rate else round(rate_val / 2, 2)
            tax.igst_rate = float(igst_rate) if igst_rate else rate_val
            tax.description = description
            if is_default and not tax.is_default:
                TaxMaster.objects.filter(is_deleted=False).update(is_default=False)
            tax.is_default = is_default
            tax.save()
            log_activity(request, "UPDATE", "TaxMaster", tax.name, object_id=tax.id, description=f"Tax Slab '{name}' ({rate_val}%) updated.")
            messages.success(request, f"Tax slab '{name}' updated successfully!")
            return redirect('tax_list')
        except Exception as e:
            messages.error(request, f"Error updating tax slab: {str(e)}")

    context = {'tax': tax, 'page_title': 'Edit Tax Slab (GST)'}
    return render(request, 'tax_master/tax_form.html', context)

@login_required
def tax_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Tax Slabs.")
        return redirect('tax_list')
    tax = get_object_or_404(TaxMaster, pk=pk)
    tax.is_deleted = True
    tax.save()
    log_activity(request, "DELETE", "TaxMaster", tax.name, object_id=tax.id, description=f"Tax Slab '{tax.name}' soft deleted.")
    messages.success(request, f"Tax slab '{tax.name}' deleted successfully!")
    return redirect('tax_list')


# ==================== SCHEDULE MASTER (DRUG SCHEDULES) VIEWS ====================
@login_required
def schedule_list(request):
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Schedule Master.")
        return redirect('home')
    ensure_default_tax_and_schedules()
    schedules = ScheduleMaster.objects.filter(is_deleted=False).order_by('name')
    context = {
        'schedules': schedules,
        'page_title': 'Schedule Master (Drug Schedules)'
    }
    return render(request, 'schedule_master/schedule_list.html', context)

@login_required
def schedule_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Drug Schedules.")
        return redirect('schedule_list')
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        warning_text = request.POST.get('warning_text', '')
        requires_prescription = request.POST.get('requires_prescription') == 'on' or request.POST.get('requires_prescription') == 'true'

        schedule = ScheduleMaster(
            name=name,
            code=code,
            warning_text=warning_text,
            requires_prescription=requires_prescription,
            created_by=request.user if request.user.is_authenticated else None
        )
        schedule.save()
        log_activity(request, "CREATE", "ScheduleMaster", schedule.name, object_id=schedule.id, description=f"Schedule '{name}' ({code}) created.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'id': schedule.id, 'name': schedule.name, 'code': schedule.code})
            
        messages.success(request, f"Schedule '{name}' created successfully!")
        return redirect('schedule_list')

    context = {'page_title': 'Add New Drug Schedule'}
    return render(request, 'schedule_master/schedule_form.html', context)

@login_required
def schedule_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Drug Schedules.")
        return redirect('schedule_list')
    schedule = get_object_or_404(ScheduleMaster, pk=pk, is_deleted=False)
    if request.method == 'POST':
        schedule.name = request.POST.get('name')
        schedule.code = request.POST.get('code')
        schedule.warning_text = request.POST.get('warning_text', '')
        schedule.requires_prescription = request.POST.get('requires_prescription') == 'on' or request.POST.get('requires_prescription') == 'true'
        schedule.save()
        log_activity(request, "UPDATE", "ScheduleMaster", schedule.name, object_id=schedule.id, description=f"Schedule '{schedule.name}' updated.")
        messages.success(request, f"Schedule '{schedule.name}' updated successfully!")
        return redirect('schedule_list')

    context = {'schedule': schedule, 'page_title': 'Edit Drug Schedule'}
    return render(request, 'schedule_master/schedule_form.html', context)

@login_required
def schedule_delete(request, pk):
    if not has_feature_access(request.user, 'product_delete'):
        messages.error(request, "Access Denied: You do not have permission to delete Drug Schedules.")
        return redirect('schedule_list')
    schedule = get_object_or_404(ScheduleMaster, pk=pk)
    schedule.is_deleted = True
    schedule.save()
    log_activity(request, "DELETE", "ScheduleMaster", schedule.name, object_id=schedule.id, description=f"Schedule '{schedule.name}' soft deleted.")
    messages.success(request, f"Schedule '{schedule.name}' deleted successfully!")
    return redirect('schedule_list')

