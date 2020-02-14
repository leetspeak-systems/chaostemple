from django.core.management.base import BaseCommand

from django.contrib.auth.models import User

from dossier.models import Dossier

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        '''
        Temporary command for populating the new Dossier.notes field with
        existing Dossier.memos. We did this instead of creating a custom
        migration to retain squashability. New installations do not require
        this step and there is only one installation at the time of this
        writing, so this will not screw up anyone's work. Remove this file if
        2020-01-02 was a long time ago.
        '''

        dossiers = Dossier.objects.prefetch_related('memos')
        dossiers = dossiers.filter(issue__parliament__parliament_num=150)
        for dossier in dossiers:

            memos = dossier.memos.all()

            notes = ''
            for memo in memos:
                notes += '* %s\n' % memo.content

            dossier.notes = notes
            dossier.save()

            print('.', end='', flush=True)

