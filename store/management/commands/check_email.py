import smtplib

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Check the actual server email login without sending any email.'

    def handle(self, *args, **options):
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError('Sender settings are missing. Run configure_email first.')
        connection = get_connection(fail_silently=False)
        try:
            connection.open()
        except smtplib.SMTPAuthenticationError:
            raise CommandError('Gmail rejected the actual server credentials. Run configure_email again with a fresh App Password.')
        except (OSError, smtplib.SMTPException):
            raise CommandError('Could not connect to the email provider.')
        finally:
            connection.close()
        self.stdout.write(self.style.SUCCESS('Actual server email authentication passed. No email was sent.'))
