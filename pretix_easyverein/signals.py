from typing import Dict, Optional

import datetime
import logging
from collections import OrderedDict
from django import forms
from django.core import validators
from django.db import connection, transaction
from django.db.models import Q
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_scopes import scopes_disabled
from django.utils import timezone
from easyverein import EasyvereinAPI
from easyverein.models.invoice import Invoice as EVInvoice
from pretix.base.forms import SecretKeySettingsField
from pretix.base.signals import periodic_task, register_global_settings
from pretix.control.permissions import organizer_permission_required
from pretix.control.signals import nav_organizer
from pretix.helpers.database import OF_SELF
from pretix.plugins.banktransfer.models import BankImportJob
from pydantic_core import Url

from .tasks import eV_import

logger = logging.getLogger(__name__)


def get_ev_invoices(ev_client: EasyvereinAPI) -> Dict[str, EVInvoice]:
    return {
        i.invNumber: i
        for i in ev_client.invoice.get_all(limit_per_page=1000)
        if i.invNumber is not None
    }


def find_ev_invoice(pt_i, ev_invoices: Dict[str, EVInvoice]) -> Optional[EVInvoice]:
    # exact invoice number match
    if pt_i["number"] in ev_invoices:
        return ev_invoices[pt_i["number"]]

    finds = []
    for ev_i in ev_invoices.values():
        # filename match
        if (
            isinstance(ev_i.path, Url)
            and ev_i.path.query is not None
            and pt_i["number"] in ev_i.path.query
        ):
            finds.append(ev_i)

    if len(finds) > 1:
        # print("not good, found too many matching:")
        # for f in finds:
        #     print(f"https://easyverein.com/app/bookkeeping/invoice/{f.id}", "#", f.invNumber)
        return None
    elif finds:
        return finds[0]


# @receiver(signal=periodic_task)
# @scopes_disabled()
# def upload_invoices_to_easyverein(sender, **kwargs):
#     ev_client = EasyvereinAPI(EV_API_KEY, auto_retry=True)
#     ev_invoices = get_ev_invoices(ev_client)

#     with transaction.atomic():
#         # process new (probably not uploaded) invoices
#         qs = Invoice.objects.filter(
#             Q(ev_sync__isnull=True) | Q(ev_sync__ev_invoice_id__isnull=True)
#         ).prefetch_related('event', 'order', 'ev_sync').select_for_update(of=OF_SELF, skip_locked=connection.features.has_select_for_update_skip_locked)
#         for i in qs:
#             print("TO PROCESS", i)

#             evs = i.ev_sync.create()
#             # search for already uploaded invoices
#             ev_i = find_ev_invoice(i.number, ev_invoices)
#             if ev_i is not None:
#                 # found
#                 # link and do not reupload
#                 evs.link2ev(ev_i.id)
#             else:
#                 # not found
#                 # upload
#                 evs.upload2ev(ev_client)
#             i.save(update_fields=['ev_sync'])


# @receiver(signal=periodic_task)
# @scopes_disabled()
# def sync_payment_status_from_easyverein(sender, **kwargs):
#     ev_client = EasyvereinAPI(EV_API_KEY, auto_retry=True)

#     # get unpayed (already uploaded) invoices
#     # fetch payment status from eV
#     # if payed -> mark payed in pretix
#     # TODO also sync
# # alert for refunds


@receiver(signal=periodic_task)
@scopes_disabled()
def bankimport_from_easyverein(sender, **kwargs):
    # make sure this runs only every 6 hours
    try:
        last_import = BankImportJob.objects.latest("created").created
        if last_import + datetime.timedelta(hours=6) > timezone.now():
            # nothing todo
            return
    except BankImportJob.DoesNotExist:
        pass

    eV_import()


@organizer_permission_required("can_change_organizer_settings")
@receiver(nav_organizer)
def add_easyverein_settings_to_nav_pane(sender, request, **kwargs):
    """
    This signal is used to add the 'Easyverein' column to the navigation pane.
    """
    return [
        {
            "label": _("Easyverein"),
            "url": reverse(
                "plugins:pretix_easyverein:settings",
                kwargs={"organizer": request.organizer.slug},
            ),
            "parent": reverse(
                "plugins:banktransfer:import",
                kwargs={"organizer": request.organizer.slug},
            ),
            "active": (request.resolver_match.url_name.startswith("settings")),
        }
    ]


@receiver(register_global_settings)
def register_global_settings_easyverein(sender, **kwargs):
    return OrderedDict(
        [
            (
                "easyverein_api_key",
                SecretKeySettingsField(
                    label=_("EasyVerein API Key"),
                    required=False,
                ),
            ),
            (
                "easyverein_import_bankstatements",
                forms.BooleanField(
                    label=_("Import bank statements from EasyVerein"),
                    required=False,
                ),
            ),
            (
                "easyverein_account_short",
                forms.CharField(
                    max_length=32,
                    label=_("EasyVerein Organization Shortcode"),
                    required=False,
                ),
            ),
            (
                "easyverein_account_email",
                forms.EmailField(
                    label=_("EasyVerein Account Email"),
                    required=False,
                    help_text=_(
                        "Necessary to trigger and wait for onlinebanking import on eV end. Requires banking permissions."
                    ),
                ),
            ),
            (
                "easyverein_account_password",
                SecretKeySettingsField(
                    label=_("EasyVerein Account Password"),
                    required=False,
                ),
            ),
            (
                "easyverein_bankaccount_ids",
                forms.CharField(
                    max_length=128,
                    label=_("EasyVerein list of bankaccount ids to sync"),
                    required=False,
                    help_text=_(
                        'Comma-seperated list of ids, e.g. "123,4567". Find them with this API URL: '
                        "https://hexa.easyverein.com/api/v1.7/bank-account"
                    ),
                    validators=[validators.RegexValidator(r"[0-9]+(,[0-9]+)*")],
                ),
            ),
        ]
    )
