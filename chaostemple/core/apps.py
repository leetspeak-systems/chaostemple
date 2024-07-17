from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "ChaosTemple Core"

    def ready(self):
        import core.signals
