from django.urls import path
from wholesaleApp.views.expense_views import (
    expense_list,
    expense_create,
    expense_edit,
    expense_delete,
    expense_category_create
)

urlpatterns = [
    path('expense/list/', expense_list, name='expense_list'),
    path('expense/create/', expense_create, name='expense_create'),
    path('expense/edit/<int:pk>/', expense_edit, name='expense_edit'),
    path('expense/delete/<int:pk>/', expense_delete, name='expense_delete'),
    path('expense/category/create/', expense_category_create, name='expense_category_create'),
]
