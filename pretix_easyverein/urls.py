from django.urls import re_path

from .views import OrganizerSettingsFormView

urlpatterns = [
    re_path(
        r"^control/organizer/(?P<organizer>[^/]+)/banktransfers/easyverein/",
        OrganizerSettingsFormView.as_view(),
        name="settings",
    ),
]
