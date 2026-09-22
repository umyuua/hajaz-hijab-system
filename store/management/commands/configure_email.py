import getpass
import json
import smtplib
import ssl

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import get_connection


class Command(BaseCommand):
    help = 'Configure a Gmail sender locally and check SMTP authentication without sending email.'

    def handle(self, *args, **options):
        sender = input('Gmail address that will SEND emails: ').strip()
        try:
            validate_email(sender)
        except ValidationError:
            raise CommandError('Enter a valid sender email address.')
        password = getpass.getpass('Google App Password (hidden): ').replace(' ', '')
        if not password:
            raise CommandError('An App Password is required.')
        public_url = input('Website address [http://127.0.0.1:8000]: ').strip() or 'http://127.0.0.1:8000'
        if not public_url.startswith(('http://', 'https://')):
            raise CommandError('Website address must start with http:// or https://.')
        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host='smtp.gmail.com', port=587, username=sender, password=password,
                use_tls=True, use_ssl=False, timeout=15,
            )
            try:
                connection.open()
            finally:
                connection.close()
        except smtplib.SMTPAuthenticationError:
            raise CommandError('Gmail rejected the credentials. Use the sender account\'s Google App Password.')
        except (OSError, smtplib.SMTPException, ssl.SSLError):
            raise CommandError('Could not connect to Gmail. Check your internet connection and try again.')
        config = {
            'EMAIL_HOST': 'smtp.gmail.com', 'EMAIL_PORT': '587',
            'EMAIL_USE_TLS': 'true', 'EMAIL_USE_SSL': 'false',
            'EMAIL_HOST_USER': sender, 'EMAIL_HOST_PASSWORD': password,
            'DEFAULT_FROM_EMAIL': sender, 'PUBLIC_BASE_URL': public_url.rstrip('/'),
        }
        path = settings.BASE_DIR / 'email_config.local.json'
        path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Sender authentication passed. Configuration saved locally. Restart the server, then register to test inbox delivery.'))
        self.stdout.write('The saved local configuration takes priority over EMAIL_* environment variables.')
