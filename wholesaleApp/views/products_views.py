from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import logging
from wholesaleApp.models import CompanyMaster, DrugMaster, ProductTypeMaster, ProductMaster
from wholesaleApp.views.security_helpers import has_feature_access, log_activity

logger = logging.getLogger(__name__)

# ==================== COMPANY MASTER VIEWS ====================
@login_required
def company_list(request):
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Company Master.")
        return redirect('home')
    companies = CompanyMaster.objects.filter(is_deleted=False)
    context = {
        'companies': companies,
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
    if not has_feature_access(request.user, 'product_view'):
        messages.error(request, "Access Denied: You do not have permission to view Products.")
        return redirect('home')
    products = ProductMaster.objects.filter(is_deleted=False).select_related('company', 'drug_composition', 'product_type')
    context = {
        'products': products,
        'page_title': 'Product Master (Item Catalog)'
    }
    return render(request, 'products/product_list.html', context)

@login_required
def product_create(request):
    if not has_feature_access(request.user, 'product_create'):
        messages.error(request, "Access Denied: You do not have permission to add Products.")
        return redirect('product_list')
    companies = CompanyMaster.objects.filter(status=True, is_deleted=False)
    drugs = DrugMaster.objects.filter(status=True, is_deleted=False)
    types = ProductTypeMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        company_id = request.POST.get('company')
        drug_id = request.POST.get('drug_composition')
        type_id = request.POST.get('product_type')
        pack_size = request.POST.get('pack_size')
        hsn_code = request.POST.get('hsn_code', '')
        gst_rate = request.POST.get('gst_rate', 12.00)
        min_stock = request.POST.get('min_stock', 10)
        scheme_qty = request.POST.get('scheme_qty', 0)
        scheme_free = request.POST.get('scheme_free', 0)
        
        product = ProductMaster(
            name=name,
            company_id=company_id,
            drug_composition_id=drug_id if drug_id else None,
            product_type_id=type_id,
            pack_size=pack_size,
            hsn_code=hsn_code,
            gst_rate=gst_rate,
            min_stock=min_stock,
            scheme_qty=scheme_qty if scheme_qty else 0,
            scheme_free=scheme_free if scheme_free else 0,
            created_by=request.user if request.user.is_authenticated else None
        )
        product.save()
        log_activity(request, "CREATE", "ProductMaster", product.name, object_id=product.id, description=f"Product '{name}' (Pack: {pack_size}, HSN: {hsn_code}) created.")
        
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
        'page_title': 'Add New Product (Item)'
    }
    return render(request, 'products/product_form.html', context)

@login_required
def product_edit(request, pk):
    if not has_feature_access(request.user, 'product_edit'):
        messages.error(request, "Access Denied: You do not have permission to edit Products.")
        return redirect('product_list')
    product = get_object_or_404(ProductMaster, pk=pk, is_deleted=False)
    companies = CompanyMaster.objects.filter(status=True, is_deleted=False)
    drugs = DrugMaster.objects.filter(status=True, is_deleted=False)
    types = ProductTypeMaster.objects.filter(status=True, is_deleted=False)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.company_id = request.POST.get('company')
        drug_id = request.POST.get('drug_composition')
        product.drug_composition_id = drug_id if drug_id else None
        product.product_type_id = request.POST.get('product_type')
        product.pack_size = request.POST.get('pack_size')
        product.hsn_code = request.POST.get('hsn_code', '')
        product.gst_rate = request.POST.get('gst_rate', 12.00)
        product.min_stock = request.POST.get('min_stock', 10)
        product.save()
        log_activity(request, "UPDATE", "ProductMaster", product.name, object_id=product.id, description=f"Product '{product.name}' updated.")
        
        messages.success(request, 'Product updated successfully!')
        return redirect('product_list')
        
    context = {
        'product': product,
        'companies': companies,
        'drugs': drugs,
        'types': types,
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
    messages.success(request, 'Product deleted successfully!')
    return redirect('product_list')

