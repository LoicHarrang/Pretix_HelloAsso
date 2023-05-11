import logging
import requests
from django.http import HttpRequest
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from pretix.base.models import Event, OrderPayment
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.settings import GlobalSettingsObject
from pretix.multidomain.urlreverse import build_absolute_uri
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("pretix.plugins.helloasso")


class Helloasso(BasePaymentProvider):
    identifier = "helloasso"
    verbose_name = _("Helloasso")

    def __init__(self, event: Event):
        super().__init__(event)

    def payment_is_valid_session(self, request):
        return True

    def payment_form_render(self, request) -> str:
        template = get_template("pretix_helloasso/payment_form.html")
        ctx = {"request": request, "event": self.event, "settings": self.settings}
        return template.render(ctx)

    def checkout_confirm_render(self, request) -> str:
        template = get_template("pretix_helloasso/payment_confirm.html")
        ctx = {"request": request, "event": self.event, "settings": self.settings}
        return template.render(ctx)

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        gs = GlobalSettingsObject()
        # initialize transaction by calling datatrans API
        transactions_url = "https://api.helloasso-sandbox.com/v5/organizations/inter-asso/checkout-intents"
        start_url = "https://api.helloasso-sandbox.com/v5/organizations/inter-asso/checkout"
        if not gs.settings.payment_datatrans_sandbox:
            transactions_url = transactions_url.replace("-sandbox", "")
            start_url = start_url.replace("-sandbox", "")
        url_base = build_absolute_uri(
            request.event,
            "plugins:pretix_helloasso:return",
            kwargs={
                "order": payment.order.code,
            },
        )
        success_url = url_base + "?state=sucess"
        error_url = url_base + "?state=error"
        cancel_url = url_base + "?state=cancel"
        logger.info("datatrans success_url = %s" % success_url)

        webhook_url = build_absolute_uri(
            request.event,
            "plugins:pretix_helloasso:webhook",
        )
        logger.info("datatrans webhook_url = %s" % webhook_url)

        payment_methods = ["TWI"]
        if gs.settings.payment_datatrans_sandbox:
            payment_methods = ["VIS"]

        responseToken = request.post(
            "https://api.helloasso.com/oauth2/token",
            json={
                "client_id":"2f040dedad2840b7b4a10fec1d694ba8",
                "client_secret":"VUNxW+e/9b4KBB6N07A5HW5NsSDLhjFW",
                "grant_type":"client_credentials",

            },
        )

        response = requests.post(
            transactions_url,
            json={
                "totalAmount": float(payment.amount) * 100,
                "initialAmount": float(payment.amount) * 100,
                "itemName": "Adhesion Football",
                "backUrl": cancel_url,
                "errorUrl": error_url,
                "returnUrl": success_url,
                "containsDonation": false,
                "terms": [
                    {
                        "amount": float(payment.amount) * 100,
                        "date": "2023-12-12"
                    },
                ],
            },
            auth={
                'Authorization': 'Bearer ' + responseToken
            },
        )
        if not response:
            raise PaymentException(
                _("datatrans: Fehler %s: %s" % (response.status_code, response.content))
            )
        body = response.json()
        transaction_id = body["transactionId"]
        payment.info_data = {"transaction": transaction_id}
        payment.save(update_fields=["info"])

        return start_url + transaction_id