"""Rotate the explicitly enabled break-glass Django admin credential."""
import os,secrets
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction

class Command(BaseCommand):
    help='Enable and rotate, or disable, the managed backend-only administrator account.'
    def handle(self,*args,**options):
        username=os.getenv('BACKEND_ADMIN_USERNAME','openiq-admin').strip()
        if not username or len(username)>150:raise CommandError('BACKEND_ADMIN_USERNAME must contain 1–150 characters')
        enabled=os.getenv('ENABLE_BACKEND_ADMIN','0')=='1'
        with transaction.atomic():
            user=User.objects.filter(username=username).first()
            if not enabled:
                if user:user.is_staff=False;user.is_superuser=False;user.set_unusable_password();user.save()
                self.stdout.write(f'OpenIQ backend admin disabled ({username}).')
                return
            password=secrets.token_urlsafe(24)
            user,_=User.objects.get_or_create(username=username)
            user.is_active=True;user.is_staff=True;user.is_superuser=True;user.set_password(password);user.save()
        self.stdout.write(self.style.WARNING('OPENIQ BACKEND ADMIN CREDENTIAL ROTATED'))
        self.stdout.write(f'URL: /admin/\nUsername: {username}\nPassword: {password}')
        self.stdout.write(self.style.WARNING('Store this password securely; it will change on the next web-container start.'))
