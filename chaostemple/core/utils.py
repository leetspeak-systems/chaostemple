
from core.models import Dossier
from core.models import DossierStatistic

def generate_dossier_statistics(issue_id, user_id):

    result = {}
    dossiers = Dossier.objects.filter(issue_id=issue_id, user_id=user_id)
    for dossier in dossiers:
        dossier_type = dossier.dossier_type # Short-hand

        if not dossier_type in result:
            result[dossier_type] = {}

        for field in Dossier.tracker.fields:
            value = getattr(dossier, field)

            if not field in result[dossier_type]:
                result[dossier_type][field] = {}

            if not value in result[dossier_type][field]:
                result[dossier_type][field][getattr(dossier, field)] = 0

            result[dossier_type][field][value] = result[dossier_type][field][value] + 1

    DossierStatistic.objects.filter(issue_id=issue_id, user_id=user_id).delete()
    for dossier_type in result:
        for field in Dossier.tracker.fields:
            for value in result[dossier_type][field]:
                kwargs = {
                    'issue_id': issue_id,
                    'user_id': user_id,
                    'dossier_type': dossier_type,
                    field: value
                }
                stat = DossierStatistic(**kwargs)
                stat.count = result[dossier_type][field][value]
                stat.save()



