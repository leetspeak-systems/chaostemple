
from django.core.management.base import BaseCommand

from djalthingi.models import *

class Command(BaseCommand):

    help = 'Fixes committees which were constantly being re-added because of a bug'

    def handle(self, *args, **options):
        try:

            many_found = True # Just to start
            while many_found:
                many_found = False

                coms = Committee.objects.all()
                for com in coms:
                    many_coms = Committee.objects.filter(committee_xml_id=com.committee_xml_id).order_by('id')
                    if many_coms.count() > 1:
                        print 'Many found: %s' % many_coms.__str__()
                        many_found = True
                        first_com = many_coms[0]
                        update_to_first = []

                        for other_com in many_coms:
                            if other_com == first_com:
                                continue # Skip first one

                            for par in other_com.parliaments.all():
                                first_com.parliaments.add(par)

                            update_to_first.append(other_com.id)

                        CommitteeAgenda.objects.filter(committee_id__in=update_to_first).update(committee_id=first_com.id)
                        Proposer.objects.filter(committee_id__in=update_to_first).update(committee_id=first_com.id)
                        Committee.objects.filter(id__in=update_to_first).delete()

        except KeyboardInterrupt:
            quit(1)

