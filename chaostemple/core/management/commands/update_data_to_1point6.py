from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from dossier.models import Dossier
from dossier.models import DossierStatistic


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        '''
        Temporary command for updating data to conform to new functionality in
        version 1.6. See comments in code for details.

        We did this instead of creating a custom migration to retain
        squashability. New installations do not require this step and there is
        only one installation at the time of this writing, so this will not
        screw up anyone's work.

        Remove this file if 2020-03-20 was a long time ago.
        '''

        # Step 1. Generate is_useful values for dossiers.
        print('Generating usefulness information for dossiers...', end='', flush=True)
        dossiers = Dossier.objects.filter(issue__parliament__parliament_num=CURRENT_PARLIAMENT_NUM)
        for dossier in dossiers:
            dossier.save()
            print('.', end='', flush=True)
        print(' done')

        # Step 2. Delete non-useful dossiers.
        print('Deleting non-useful dossiers...', end='', flush=True)
        Dossier.objects.filter(is_useful=False).delete()
        print(' done')

        # Step 3. Turn "memos" into "notes".
        print('Turning memos into notes...', end='', flush=True)
        dossiers = Dossier.objects.prefetch_related('memos')
        dossiers = dossiers.filter(issue__parliament__parliament_num=CURRENT_PARLIAMENT_NUM)
        for dossier in dossiers:

            memos = dossier.memos.all()

            notes = ''
            for memo in memos:
                notes += '* %s\n\n' % memo.content.strip('*').strip()

            dossier.notes = notes
            dossier.save()

            print('.', end='', flush=True)
        print(' done')

        # Step 4. Update dossier statistics to reflect deletions and updates.
        print('Updating dossier statistics...', end='', flush=True)
        stats = DossierStatistic.objects.filter(issue__parliament__parliament_num=CURRENT_PARLIAMENT_NUM)
        for stat in stats:
            stat.update_stats_quite_inefficiently_please(show_output=False)
            print('.', end='', flush=True)
        print(' done')
