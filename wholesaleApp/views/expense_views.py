from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, timedelta

from wholesaleApp.models.expense import Expense, ExpenseCategory
from wholesaleApp.views.security_helpers import has_feature_access, get_user_permissions_context, log_activity
from wholesaleApp.utils.list_helpers import paginate_queryset

DEFAULT_EXPENSE_CATEGORIES = [
    ("Shop / Godown Rent", "Monthly rent for shop, store or warehouse premises"),
    ("Electricity & Power Bill", "Monthly utility electricity & generator fuel bills"),
    ("Staff Salary & Wages", "Employee salaries, daily wages, and allowances"),
    ("Tea, Refreshments & Snacks", "Daily tea, coffee, lunch, and guest refreshments"),
    ("Transportation, Freight & Courier", "Vehicle fuel, delivery charges, and courier expenses"),
    ("Stationery, Printing & Xerox", "Bill books, computer paper, barcode stickers, toner"),
    ("Shop Maintenance & Repairs", "Electrical, furniture, painting, and computer repairs"),
    ("Bank Charges & Taxes", "Bank fees, account maintenance, and professional taxes"),
    ("Miscellaneous / Daily Petty Cash", "General office petty cash & daily sundry expenses"),
]

def seed_default_expense_categories():
    """Ensure standard pharmaceutical wholesale expense heads exist."""
    for cat_name, desc in DEFAULT_EXPENSE_CATEGORIES:
        ExpenseCategory.objects.get_or_create(
            name=cat_name,
            defaults={'description': desc, 'is_active': True}
        )

@login_required
def expense_list(request):
    """Daily expense management ledger with metrics, filters, and quick entry."""
    if not (request.user.is_superuser or has_feature_access(request.user, 'expense_view') or has_feature_access(request.user, 'customer_ledger')):
        messages.error(request, "Access Denied: You do not have permission to view Expenses.")
        return redirect('home')

    seed_default_expense_categories()

    today = timezone.now().date()
    from_date = request.GET.get('from_date', today.replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.GET.get('to_date', today.strftime('%Y-%m-%d'))
    category_id = request.GET.get('category', '').strip()
    payment_mode = request.GET.get('payment_mode', '').strip()
    q = request.GET.get('q', '').strip()

    try:
        parsed_from = datetime.strptime(from_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        parsed_from = today.replace(day=1)
        from_date = parsed_from.strftime('%Y-%m-%d')

    try:
        parsed_to = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        parsed_to = today
        to_date = parsed_to.strftime('%Y-%m-%d')

    expenses = Expense.objects.all().select_related('category', 'created_by')

    if from_date and to_date:
        expenses = expenses.filter(expense_date__range=[parsed_from, parsed_to])

    if category_id and category_id.isdigit():
        expenses = expenses.filter(category_id=int(category_id))

    if payment_mode:
        expenses = expenses.filter(payment_mode=payment_mode)

    if q:
        expenses = expenses.filter(
            Q(paid_to__icontains=q) |
            Q(reference_no__icontains=q) |
            Q(remarks__icontains=q) |
            Q(category__name__icontains=q)
        )

    # Compute KPI Summaries
    filtered_total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # All expenses in database for quick stats
    all_qs = Expense.objects.all()
    today_total = all_qs.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    month_start = today.replace(day=1)
    month_total = all_qs.filter(expense_date__gte=month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_total = expenses.filter(payment_mode='Cash').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    digital_total = expenses.exclude(payment_mode='Cash').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Category breakdown for the filtered period
    category_summary = (
        expenses.values('category__id', 'category__name')
        .annotate(cat_total=Sum('amount'))
        .order_by('-cat_total')
    )

    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')

    page_data = paginate_queryset(request, expenses, default_per_page=25)

    context = {
        'expenses': page_data['page_obj'],
        'page_obj': page_data['page_obj'],
        'paginator': page_data['paginator'],
        'extra_query': page_data['extra_query'],
        'per_page': page_data['per_page'],
        'total_count': page_data['total_count'],
        'categories': categories,
        'category_summary': category_summary,
        
        # Filter values
        'from_date': from_date,
        'to_date': to_date,
        'selected_category': category_id,
        'selected_payment_mode': payment_mode,
        'q': q,

        # Metrics
        'filtered_total': filtered_total,
        'today_total': today_total,
        'month_total': month_total,
        'cash_total': cash_total,
        'digital_total': digital_total,

        'page_title': 'Expense Management (Accounts)',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'expense/expense_list.html', context)


@login_required
def expense_create(request):
    """Record a new business expense voucher."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

    if not (request.user.is_superuser or has_feature_access(request.user, 'expense_create') or has_feature_access(request.user, 'customer_ledger')):
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': "Access Denied: You do not have permission to add expenses."}, status=403)
        messages.error(request, "Access Denied: You do not have permission to add expenses.")
        return redirect('expense_list')

    seed_default_expense_categories()

    if request.method == 'POST':
        expense_date = request.POST.get('expense_date')
        category_id = request.POST.get('category')
        amount = request.POST.get('amount', '0').strip()
        payment_mode = request.POST.get('payment_mode', 'Cash')
        paid_to = request.POST.get('paid_to', '').strip()
        reference_no = request.POST.get('reference_no', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        if not expense_date or not category_id or not amount:
            err_msg = "Expense Date, Category, and Amount are required."
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('expense_create')

        try:
            amt_val = Decimal(amount)
            if amt_val <= 0:
                raise ValueError()
        except Exception:
            err_msg = "Please enter a valid positive amount."
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('expense_create')

        category = get_object_or_404(ExpenseCategory, id=category_id)

        expense = Expense.objects.create(
            expense_date=expense_date,
            category=category,
            amount=amt_val,
            payment_mode=payment_mode,
            paid_to=paid_to,
            reference_no=reference_no,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None
        )

        log_activity(
            request,
            action='CREATE',
            model_name='Expense',
            object_id=expense.id,
            object_repr=f"Expense #{expense.id} ({category.name})",
            description=f"Recorded expense of ₹{amt_val} for {category.name} ({payment_mode})"
        )

        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'message': f"Expense of ₹{amt_val:.2f} recorded successfully for {category.name}!",
                'id': expense.id,
                'category_name': category.name,
                'amount': float(expense.amount),
                'date': str(expense.expense_date)
            })

        messages.success(request, f"Expense of ₹{amt_val:.2f} recorded successfully for {category.name}!")
        return redirect('expense_list')

    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    context = {
        'categories': categories,
        'today': timezone.now().date().strftime('%Y-%m-%d'),
        'page_title': 'Record Daily Expense',
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'expense/expense_form.html', context)


@login_required
def expense_edit(request, pk):
    """Edit an existing expense voucher."""
    if not (request.user.is_superuser or has_feature_access(request.user, 'expense_edit') or has_feature_access(request.user, 'customer_ledger')):
        messages.error(request, "Access Denied: You do not have permission to edit expenses.")
        return redirect('expense_list')

    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        expense.expense_date = request.POST.get('expense_date')
        category_id = request.POST.get('category')
        amount = request.POST.get('amount', '0').strip()
        expense.payment_mode = request.POST.get('payment_mode', 'Cash')
        expense.paid_to = request.POST.get('paid_to', '').strip()
        expense.reference_no = request.POST.get('reference_no', '').strip()
        expense.remarks = request.POST.get('remarks', '').strip()

        if category_id:
            expense.category_id = category_id
        if amount:
            expense.amount = Decimal(amount)

        expense.save()

        log_activity(
            request,
            action='UPDATE',
            model_name='Expense',
            object_id=expense.id,
            object_repr=f"Expense #{expense.id}",
            description=f"Updated expense voucher #{expense.id} to ₹{expense.amount} ({expense.category.name})"
        )

        messages.success(request, f"Expense voucher updated successfully!")
        return redirect('expense_list')

    categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    context = {
        'expense': expense,
        'categories': categories,
        'page_title': f"Edit Expense Voucher #{expense.id}",
        'user_perms': get_user_permissions_context(request.user)
    }
    return render(request, 'expense/expense_form.html', context)


@login_required
def expense_delete(request, pk):
    """Delete an expense voucher."""
    if not (request.user.is_superuser or has_feature_access(request.user, 'expense_delete') or has_feature_access(request.user, 'customer_ledger')):
        messages.error(request, "Access Denied: You do not have permission to delete expenses.")
        return redirect('expense_list')

    expense = get_object_or_404(Expense, pk=pk)
    cat_name = expense.category.name
    amt = expense.amount
    expense_id = expense.id

    expense.delete()

    log_activity(
        request,
        action='DELETE',
        model_name='Expense',
        object_id=expense_id,
        object_repr=f"Expense #{expense_id}",
        description=f"Deleted expense of ₹{amt} ({cat_name})"
    )

    messages.success(request, f"Expense voucher of ₹{amt} deleted successfully.")
    return redirect('expense_list')


@login_required
def expense_category_create(request):
    """Create a new expense category head (supports AJAX)."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

    if not (request.user.is_superuser or has_feature_access(request.user, 'expense_create') or has_feature_access(request.user, 'customer_ledger')):
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': "Access Denied: Permission required."}, status=403)
        messages.error(request, "Access Denied: You do not have permission to create expense categories.")
        return redirect('expense_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': "Category Name is required."}, status=400)
            messages.error(request, "Category Name is required.")
            return redirect('expense_list')

        if ExpenseCategory.objects.filter(name__iexact=name).exists():
            existing = ExpenseCategory.objects.filter(name__iexact=name).first()
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Category '{name}' already exists.",
                    'id': existing.id,
                    'name': existing.name
                }, status=400)
            messages.error(request, f"Category '{name}' already exists.")
            return redirect('expense_list')

        category = ExpenseCategory.objects.create(
            name=name,
            description=description,
            created_by=request.user if request.user.is_authenticated else None
        )

        if is_ajax:
            return JsonResponse({
                'status': 'success',
                'message': f"Expense Category '{name}' created successfully!",
                'id': category.id,
                'name': category.name
            })

        messages.success(request, f"Expense Category '{name}' created successfully!")
        return redirect('expense_list')

    return redirect('expense_list')
