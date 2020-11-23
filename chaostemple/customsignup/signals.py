from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from djalthingi.models import Committee
from djalthingi.models import Person

from core.models import Access
from core.models import AccessUtilities
from core.models import UserProfile
from core.models import Subscription

from django.contrib.auth.models import User


@receiver(user_logged_in)
def auto_subscription(sender, request, user, **kwargs):
    '''
    During login, automatically subscribe a user to their appropriate things.
    For example, users that are members of a committee should be subscribed
    to that committee.
    '''

    # Access information will need to be available to the subscription
    # mechanism which gets activated if Subscription objects are saved below.
    # This has the side-effect that `cache_access` is run twice during login,
    # once here and once in the regular access-middleware. Shouldn't matter.
    AccessUtilities.cache_access(user)

    # Find committees to which the recently logged in user is a member.
    committees = Committee.objects.currently_with_person(
        user.userprofile.person
    ).exclude(
        subscriptions__user=user
    )

    # Subscribe the user to the committees they should be subscribed to.
    for committee in committees:
        Subscription.objects.get_or_create(user_id=user.id, committee_id=committee.id)


@receiver(post_save, sender=Person)
@receiver(post_save, sender=User)
def configure_person_and_userprofile(sender, instance, **kwargs):
    '''When a Person or User is saved, check if they can be matched by email'''

    if sender is Person and instance.email:
        try:
            user = User.objects.get(email=instance.email)
            person = instance
        except User.DoesNotExist:
            # There is no user, thus no userprofile to configure. We're done here.
            return

    elif sender is User:
        user = instance
        person = None
        if instance.email:
            try:
                person = Person.objects.get(email=instance.email)
            except Person.DoesNotExist:
                pass
    else:
        # Shouldn't happen, but whatever.
        return

    # At this point, the user object is guaranteed to exist.

    # Ensure the existence of a userprofile.
    try:
        userprofile = UserProfile.objects.get(user_id=user.id)
    except UserProfile.DoesNotExist:
        userprofile = UserProfile(user_id=user.id)

    # Configure userprofile according to information about the associated person.
    if person is not None:
        last_seat = person.seats.select_related('party').last()

        userprofile.person = person
        userprofile.name = person.name
        userprofile.initials = last_seat.name_abbreviation

        # Get the group corresponding to the party, if it exists. Otherwise,
        # create it, and add the user to it. This ensures that people in the
        # same party all belong to the same group.
        group, created = Group.objects.get_or_create(name=last_seat.party.name)
        group.user_set.add(user)

        # Automatically give access to everyone in the party group. Note that
        # a user can choose to strip access from his own group by removing the
        # full access.
        access, created = Access.objects.get_or_create(user_id=user.id, friend_group_id=group.id)
        if created:
            access.full_access = True
            access.save()

    # Finally, save the profile.
    userprofile.save()
