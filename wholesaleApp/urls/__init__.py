from wholesaleApp.urls.master import urlpatterns as masterurl
from wholesaleApp.urls.customers import urlpatterns as customerurl
from wholesaleApp.urls.supplier import urlpatterns as supplierurl
from wholesaleApp.urls.products import urlpatterns as producturl
from wholesaleApp.urls.purchase import urlpatterns as purchaseurl
from wholesaleApp.urls.sales import urlpatterns as salesurl
from wholesaleApp.urls.reports import urlpatterns as reportsurl
from wholesaleApp.urls.scheme import urlpatterns as schemeurl
from wholesaleApp.urls.financial_year import urlpatterns as fyurl


urlpatterns = masterurl + customerurl + supplierurl + producturl + purchaseurl + salesurl + reportsurl + schemeurl + fyurl

