from django import forms
from django.core import validators
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SecretKeySettingsField, SettingsForm


class OrganizerEasyvereinSettingsForm(SettingsForm):
    easyverein_api_key = SecretKeySettingsField(
        label=_("EasyVerein API Key"), required=False
    )

    easyverein_import_bankstatements = forms.BooleanField(
        label=_("Import bank statements from EasyVerein"), required=False
    )

    easyverein_import_bankstatements = forms.BooleanField(
        label=_("Import bank statements from EasyVerein"),
        required=False,
    )

    easyverein_account_short = forms.CharField(
        max_length=32,
        label=_("EasyVerein Organization Shortcode"),
        required=False,
    )

    easyverein_account_email = forms.EmailField(
        label=_("EasyVerein Account Email"),
        required=False,
        help_text=_(
            "Necessary to trigger and wait for onlinebanking import on eV end. Requires banking permissions."
        ),
    )

    easyverein_account_password = SecretKeySettingsField(
        label=_("EasyVerein Account Password"),
        required=False,
    )

    easyverein_bankaccount_ids = forms.CharField(
        max_length=128,
        label=_("EasyVerein list of bankaccount ids to sync"),
        required=False,
        help_text=_('Comma-seperated list of ids, e.g. "54477743,54477747".'),
        validators=[validators.RegexValidator(r"[0-9]+(,[0-9]+)*")],
    )
