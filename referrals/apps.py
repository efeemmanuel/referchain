


from django.apps import AppConfig


class ReferralsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'referrals'

    def ready(self):
        """
        Import signals when the app is ready.
        This is the correct place to connect signals in Django.
        Without this, the signal handler never gets registered
        and emails will never be sent.
        """
        import referrals.signals