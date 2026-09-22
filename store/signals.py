import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def email_notification(sender, instance, created, raw=False, **kwargs):
    if not created or raw or not instance.user.is_active or not instance.user.email:
        return
    recipient = instance.user.email
    body = instance.message

    def deliver():
        try:
            if send_mail('Hajaz Hijab account update', body,
                         settings.DEFAULT_FROM_EMAIL, [recipient],
                         fail_silently=False) != 1:
                raise RuntimeError('Email backend did not accept the notification.')
        except Exception:
            logger.exception('Unable to deliver notification email %s', instance.pk)

    transaction.on_commit(deliver)
