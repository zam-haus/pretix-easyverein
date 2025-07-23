import logging
from django.urls import reverse
from pretix.base.models import Organizer
from pretix.celery_app import app
from pretix.plugins.banktransfer.models import BankImportJob, BankTransaction
from pretix.plugins.banktransfer.tasks import process_banktransfers

from .ev_utils import eV_get_bankstatements, eV_trigger_and_wait_for_onlinebankingimport

logger = logging.getLogger(__name__)


@app.task
def eV_import():
    bankstatements_per_key = dict()

    for org in Organizer.objects.all():
        logger.info(f"Bank import from easyverein for {org}.")
        # Skip orgs that have import not configured
        if org.settings.get("easyverein_import_bankstatements") is None:
            continue

        ev_api_key = org.settings.get("easyverein_api_key")
        # Skip (and log) orgs that have it configured, but no api key
        if ev_api_key is None:
            logger.warning(
                f"{org} has easyverein_import_bankstatements enabled, "
                "but no easyverein_api_key configured."
            )
            continue

        # get bank statement from easyverein
        if ev_api_key in bankstatements_per_key:
            bankstatement = bankstatements_per_key[ev_api_key]
        else:
            # Trigger import eV to import from banks
            eV_trigger_and_wait_for_onlinebankingimport(
                org.settings.get("easyverein_account_short"),
                org.settings.get("easyverein_account_email"),
                org.settings.get("easyverein_account_password"),
                bankaccount_ids=[
                    id
                    for id in org.settings.get("easyverein_bankaccount_ids").split(",")
                ],
            )

            # Import bankstatement from eV
            logger.info("Fetching bankstatement from eV.")
            bankstatement = eV_get_bankstatements(ev_api_key, days_back=8)
            bankstatements_per_key[ev_api_key] = bankstatement

        # create import job
        job = BankImportJob.objects.create(organizer=org, currency="EUR")
        process_banktransfers.apply_async(kwargs={"job": job.pk, "data": bankstatement})
        kwargs = {"organizer": org, "job": job.pk}

        logger.info(
            f"Bank import from easyverein for {org} finished: {reverse('plugins:banktransfer:import.job', kwargs=kwargs)} "
            f"{job.transactions.filter(state=BankTransaction.STATE_VALID).count()} matched."
        )

        # auto discard all unmatched transaction for data minimization
        # job.transactions.filter(state=BankTransaction.STATE_NOMATCH).update(payer='', reference='', amount=0, state=BankTransaction.STATE_DISCARDED)
