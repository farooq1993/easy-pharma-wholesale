from django.contrib import admin
from wholesaleApp.models.supplier import (SupplierMaster)
from wholesaleApp.models.customers import (AreaMaster, CustomerMaster, SubareaMaster)
from wholesaleApp.models.tenant import (Tenant, TenantEmailConfig)

# Register your models here.

admin.site.register(SupplierMaster)
admin.site.register(AreaMaster)
admin.site.register(CustomerMaster)
admin.site.register(SubareaMaster)
admin.site.register(Tenant)
admin.site.register(TenantEmailConfig)

