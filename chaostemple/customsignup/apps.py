from django.apps import AppConfig

class CustomsignupConfig(AppConfig):
    name = 'customsignup'
    verbose_name = 'ChaosTemple CustomSignup'

    def ready(self):
        import customsignup.signals
