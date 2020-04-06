from djalthingi.models import Person
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

# If only a slug, but no subslug is provided to a URL that shows a person, we
# try to figure out who the person is and if we can't, we ask the user which
# one is being requested and redirect the user accordingly to the same page
# with the subslug selected.
#
# The target URL is expected to accept "slug" and "subslug" but may also
# accept others, which will be included automatically in the redirection.
#
# Supports only views with named parameters.
#
def complete_person(request, slug):
    persons = Person.objects.filter(slug=slug).order_by('-birthdate')
    if persons.count() > 1:

        # Make a list of possible persons that the user might be referring to.
        possibles = []
        for person in persons:
            kwargs = request.resolver_match.kwargs
            kwargs['subslug'] = person.subslug
            url = reverse(request.resolver_match.url_name, kwargs=kwargs)
            possibles.append({
                'name': person.name,
                'birthyear': person.birthdate.year,
                'url': url,
            })

        return render(request, 'core/person_select_from_multiple.html', { 'possibles': possibles })

    elif persons.count() == 1:

        kwargs = request.resolver_match.kwargs
        kwargs['subslug'] = persons[0].subslug
        return redirect(reverse(request.resolver_match.url_name, kwargs=kwargs))

    else:
        raise Http404
