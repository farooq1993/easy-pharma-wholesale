from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
import hashlib
import json
import time

def get_cache_version(prefix, tenant_id=None):
    """Retrieve or initialize the cache version for a specific list prefix and tenant."""
    v_key = f"{prefix}_ver_{tenant_id or 'all'}"
    version = cache.get(v_key)
    if not version:
        version = int(time.time() * 1000)
        cache.set(v_key, version, timeout=86400)
    return version

def invalidate_list_cache(prefix, tenant_id=None):
    """Atomically bump cache version to invalidate all cached list queries for prefix."""
    v_key = f"{prefix}_ver_{tenant_id or 'all'}"
    current = cache.get(v_key)
    if current is not None and isinstance(current, int):
        new_version = current + 1
    else:
        new_version = int(time.time() * 1000)
    cache.set(v_key, new_version, timeout=86400)
    # Also invalidate global 'all' if tenant-specific
    if tenant_id:
        all_key = f"{prefix}_ver_all"
        curr_all = cache.get(all_key)
        new_all = (curr_all + 1) if (curr_all is not None and isinstance(curr_all, int)) else int(time.time() * 1000)
        cache.set(all_key, new_all, timeout=86400)
    return new_version

def make_cache_key(prefix, tenant_id, params_dict):
    """Construct a deterministic cache key based on version and query parameters."""
    version = get_cache_version(prefix, tenant_id)
    # Sort keys for deterministic JSON serialization
    serialized = json.dumps(params_dict, sort_keys=True, default=str)
    param_hash = hashlib.md5(serialized.encode('utf-8')).hexdigest()[:12]
    return f"{prefix}_{tenant_id or 'all'}_v{version}_{param_hash}"

def paginate_queryset(request, queryset, default_per_page=25, allowed_per_page=(10, 25, 50, 100)):
    """
    Standard server-side paginator helper.
    Preserves all active request GET query parameters in extra_query string.
    """
    try:
        per_page = int(request.GET.get('per_page', default_per_page))
        if per_page not in allowed_per_page:
            per_page = default_per_page
    except (ValueError, TypeError):
        per_page = default_per_page

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    # Build query string excluding 'page' to append to pagination links
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    extra_query = params.urlencode()

    return {
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'extra_query': extra_query,
        'total_count': paginator.count
    }
