from django.utils.translation import gettext_lazy

from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_easyverein"
    verbose_name = "Pretix-easyVerein"

    class PretixPluginMeta:
        name = gettext_lazy("Pretix-easyVerein")
        author = "Julian Hammer"
        description = gettext_lazy("Connects pretix with easyverein")
        visible = True
        version = __version__
        category = "INTEGRATION"
        compatibility = "pretix>=2024.11.0.dev0"
        settings_links = []
        navigation_links = []
        restricted = True

    def ready(self):
        from . import signals  # NOQA
