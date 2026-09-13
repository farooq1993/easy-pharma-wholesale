"""
WSGI config for easyPharma_wholesale project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easyPharma_wholesale.settings')

application = get_wsgi_application()
app = application

# Vercel Serverless Hack: Auto-run migrations on boot since Vercel's legacy python builder doesn't run build scripts
if os.environ.get('VERCEL') == '1':
    try:
        from django.core.management import call_command
        print("Auto-running migrations for Vercel...")
        call_command('migrate', interactive=False)
    except Exception as e:
        print("Vercel auto-migrate failed:", e)
