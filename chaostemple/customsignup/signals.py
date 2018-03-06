from django.db.models.signals import post_save
from django.dispatch import receiver

from althingi.models import Person

from core.models import UserProfile

from django.contrib.auth.models import User


@receiver(post_save, sender=Person)
@receiver(post_save, sender=User)
def designate_person_to_userprofile(sender, instance, **kwargs):
    '''When a Person or User is saved, check if they can be matched by email'''

    if sender is Person and instance.email:
        try:
            user = User.objects.get(email=instance.email)
            person = instance
        except User.DoesNotExist:
            return

    elif sender is User and instance.email:
        try:
            user = instance
            person = Person.objects.get(email=instance.email)
        except Person.DoesNotExist:
            return
    else:
        return

    try:
        UserProfile.objects.get(user_id=user.id)
    except UserProfile.DoesNotExist:
        user.userprofile = UserProfile(user_id=user.id)

    user.userprofile.person = person
    user.userprofile.name = person.name
    user.userprofile.initials = user.userprofile.person.seats.last().name_abbreviation
    user.userprofile.save()


@receiver(post_save, sender=User)
def ensure_userprofile(sender, instance, **kwargs):
    try:
        userprofile = instance.userprofile
    except UserProfile.DoesNotExist:
        instance.userprofile = UserProfile(user_id=instance.id)
        instance.userprofile.save()
