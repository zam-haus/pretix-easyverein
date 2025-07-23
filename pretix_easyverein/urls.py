from django.urls import include, re_path

from pretix.multidomain import event_url

from .views import (
    OrganizerSettingsFormView
)

urlpatterns = [
    re_path(r'^control/organizer/(?P<organizer>[^/]+)/banktransfers/easyverein/',
            OrganizerSettingsFormView.as_view(), name='settings'),
]