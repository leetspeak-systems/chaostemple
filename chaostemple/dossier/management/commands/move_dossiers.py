from django.core.management.base import BaseCommand

from sys import stdout

from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM

from djalthingi.exceptions import DataIntegrityException

from djalthingi.models import Review

from dossier.models import Dossier

class Command(BaseCommand):
    help = 'Safely moves dossiers from one review to another.'

    def add_arguments(self, parser):
        parser.add_argument('source_review_log_num', nargs=1, type=int)
        parser.add_argument('target_review_log_num', nargs=1, type=int)
        parser.add_argument('parliament_num', nargs='?', type=int)

    def handle(self, *args, **options):
        source_review_log_num = options['source_review_log_num'][0]
        target_review_log_num = options['target_review_log_num'][0]
        parliament_num = options['parliament_num'] or CURRENT_PARLIAMENT_NUM

        source = Review.objects.select_related('issue').get(
            log_num=source_review_log_num,
            issue__parliament__parliament_num=parliament_num
        )

        target = Review.objects.get(
            log_num=target_review_log_num,
            issue__parliament__parliament_num=parliament_num
        )

        # First, let's make sure that only useless dossiers exist on the
        # target, because we'd like to remove them before moving them from
        # source to target.
        for dossier in target.dossiers.select_related('user').all():
            if not dossier.is_useful:
                stdout.write('Deleting useless dossier for user %s...' % dossier.user)
                stdout.flush()

                dossier.delete()

                stdout.write(' done\n')
            else:
                raise DataIntegrityException('Useful dossier found for user %s in target' % dossier.user)

        for dossier in source.dossiers.select_related('user').all():
            stdout.write('Moving dossier for user %s...' % dossier.user)
            stdout.flush()

            dossier.review_id = target.id
            dossier.save()

            stdout.write(' done\n')

        # Then, let's calculate all the dossier statistics again.
        # Slowly, as requested.
        for stat in source.issue.dossierstatistic_set.select_related('user').all():
            stdout.write('Recalculating dossier statistics for user %s...' % stat.user)
            stdout.flush()

            stat.update_stats_quite_inefficiently_please()

            stdout.write(' done\n')
