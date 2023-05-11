from collections import OrderedDict
from django import forms
from django.dispatch import receiver
from pretix.base.signals import register_global_settings, register_payment_providers


@receiver(register_payment_providers, dispatch_uid="payment_helloasso")
def register_payment_provider(sender, **kwargs):
    from .payment import Helloasso

    return Helloasso


@receiver(register_global_settings, dispatch_uid="helloasso_global_settings")
def register_global_settings(sender, **kwargs):
    return OrderedDict(
        [
            (
                "payment_helloasso_sandbox",
                forms.BooleanField(
                    label="Helloasso: Use Sandbox",
                    required=False,
                ),
            ),
            (
                "payment_helloasso_merchant_id",
                forms.CharField(
                    label="Helloasso: Client ID",
                    required=False,
                ),
            ),
            (
                "payment_helloasso_api_password",
                forms.CharField(
                    label="Helloasso: API password",
                    required=False,
                ),
            ),
            (
                "payment_datatrans_hmac_signing_key",
                forms.CharField(
                    label="Datatrans: HMAC Signing Key (Webhook)",
                    required=False,
                ),
            ),
        ]
    )
