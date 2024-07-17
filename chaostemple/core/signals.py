from django.db.models.signals import pre_delete
from django.dispatch import receiver

from djalthingi.exceptions import DataIntegrityException

from djalthingi.models import Document
from djalthingi.models import Review

from dossier.models import Dossier


@receiver(pre_delete, sender=Review)
@receiver(pre_delete, sender=Document)
def delete_dossiers_on_deletion(sender, instance, **kwargs):
    if sender is Document:
        dossier_kwargs = {"document_id": instance.id}
    elif sender is Review:
        dossier_kwargs = {"review_id": instance.id}
    else:
        return  # Shouldn't happen, but better safe than sorry.

    dossiers = Dossier.objects.filter(**dossier_kwargs)
    for dossier in dossiers:
        if dossier.is_useful:
            if sender is Review:
                # This is a review that is about to be deleted, but it has a
                # user-generated dossier attached to it with useful
                # information, which we shouldn't delete. Instead, we'll throw
                # an exception with enough information included for an
                # administrator or developer to handle the problem as quickly
                # and easily as possible.

                # Sometimes reviews are deleted and added again for some
                # reason. One relatively common reason is that its sender
                # sends in a new review with additional information. Such
                # reviews are not updated (and possibly cannot be, due to
                # formalities in their processing) but rather their old
                # version is removed and the new version added. Such reviews
                # will be from the same sender and be of the same type, but
                # their dates may differ. However, the same sender may also
                # send in more than one review with the same type, so we can't
                # trust that such reviews are the same as the one being
                # deleted. Thus the matter must be resolved with manual
                # intervention.

                # If there is another review in the same issue with the same
                # sender and type, well want to mention that in our exception.

                review = dossier.review

                msg = "Useful dossier found when trying to delete review."
                msg += " User: %s." % dossier.user
                msg += " Sender: %s." % review.sender_name
                msg += " Review log_num: %d." % review.log_num
                msg += " Issue: %d/%d." % (
                    review.issue.issue_num,
                    review.issue.parliament.parliament_num,
                )

                potential_replacements = Review.objects.filter(
                    issue_id=review.issue_id,
                    review_type=review.review_type,
                    sender_name=review.sender_name,
                ).exclude(id=review.id)

                if len(potential_replacements):
                    log_nums = [str(r.log_num) for r in potential_replacements]
                    msg += " Potential replacements (log_nums): %s." % ", ".join(
                        log_nums
                    )
                else:
                    msg += " No potential replacements found."

                raise DataIntegrityException(msg)

        else:
            # We can safely delete this dossier, since it's not useful.
            dossier.delete()
