from typing import List

import datetime
import easyverein
import logging
import re
import requests
import time
from easyverein.models import BookingFilter

logger = logging.getLogger(__name__)


def _eV_set_csrfheader_from_response(
    response: requests.Response, session: requests.Session
) -> str:
    csrf_match = re.search(
        r'<input type="hidden" name="csrfmiddlewaretoken" value="([a-zA-Z0-9]+)">',
        response.text,
    )
    if csrf_match:
        csrf_token = csrf_match.groups()[0]
    else:
        raise Exception("CSRF token not found.")
    session.headers["X-CSRFToken"] = csrf_token
    return csrf_token


def _eV_login(short, email, password) -> requests.Session:
    s = requests.Session()
    url = "https://easyverein.com/app/"
    r = s.get(url)
    csrf_token = _eV_set_csrfheader_from_response(r, s)
    data = {
        "csrfmiddlewaretoken": csrf_token,
        "short": short,
        "email": email,
        "password": password,
        "loginbutton": "",
    }
    s.headers["Referer"] = "https://easyverein.com/app/"
    r = s.post(url, data)
    _eV_set_csrfheader_from_response(r, s)
    return s


def _eV_onlinebankingimport(session: requests.Session, bankaccount_ids: List[str]):
    r = session.get("https://easyverein.com/app/bookkeeping/")
    _eV_set_csrfheader_from_response(r, session)
    url = "https://easyverein.com/app/finapi/onlinebankingimport/"
    r = session.post(url, json={"bankAccounts": bankaccount_ids})
    r.raise_for_status()
    _eV_poll_for_onlinebankingimport_completion(session)


def _eV_poll_for_onlinebankingimport_completion(session: requests.Session):
    logger.info("Waiting for any eV onlinebanking tasks to complete.")
    url = "https://easyverein.com/app/api/get-tasks/"
    retry = True
    while retry:
        r = session.get(url)
        r.raise_for_status()
        retry = False
        for task in r.json()["tasks"]:
            if (
                "details" not in task
                or "mode" not in task["details"]
                or task["details"]["mode"] != "ONLINEBANKING_IMPORT"
            ):
                # only handle onlinebanking import tasks
                continue
            if task["state"] == "SUCCESS":
                _eV_remove_task(session, task["id"])
                pass
            elif task["state"] == "PROGRESS":
                # wait and retry
                time.sleep(5)
                retry = True
                break
    logger.info("All eV onlinebanking tasks completed.")


def _eV_remove_task(session: requests.Session, task_id: str):
    r = session.get(f"https://easyverein.com/app/api/delete-task/{task_id}")
    r.raise_for_status()


def eV_trigger_and_wait_for_onlinebankingimport(
    short, email, password, bankaccount_ids
):
    session = _eV_login(short, email, password)
    logger.info("Triggering eV onlinebanking import.")
    _eV_onlinebankingimport(session, bankaccount_ids)


def eV_get_bankstatements(api_key, days_back=None):
    ev = easyverein.EasyvereinAPI(api_key)

    search_filter = None
    if days_back:
        search_filter = BookingFilter(
            date__gt=(
                datetime.datetime.now() - datetime.timedelta(days=days_back)
            ).replace(hour=0, minute=0, second=0, microsecond=0)
        )

    bookings = ev.booking.get_all(
        query="{date,amount,description,receiver,counterpartIban,counterpartBic}",
        search=search_filter,
        limit_per_page=100,
    )

    # ["date", "amount", "reference", "payer", "IBAN", "BIC"]
    statement = []
    for b in bookings:
        # filter outgoing payments. not relevant to pretix
        if b.amount and b.amount < 0:
            continue

        # mandatory entries:
        row = {}
        if b.date:
            # convert date to str. pretix will convert back to date
            row["date"] = str(b.date.date())
        else:
            continue
        if b.amount:
            # convert float to str. pretix will convert to Decimal
            row["amount"] = str(b.amount)
        else:
            continue
        if b.description:
            row["reference"] = b.description
        else:
            continue

        # optional entries:
        if b.receiver:
            row["payer"] = b.receiver
        if b.counterpartIban:
            row["iban"] = b.counterpartIban
        if b.counterpartBic:
            row["bic"] = b.counterpartBic

        statement.append(row)

    return statement
