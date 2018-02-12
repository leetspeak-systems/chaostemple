
from django.core.management.base import BaseCommand
from django.utils import timezone

from althingi.models import Parliament

from althingi.updaters import update_committee
from althingi.updaters import update_committee_agenda
from althingi.updaters import update_committee_agendas
from althingi.updaters import update_committees
from althingi.updaters import update_constituencies
from althingi.updaters import update_issues
from althingi.updaters import update_issue
from althingi.updaters import update_next_sessions
from althingi.updaters import update_next_committee_agendas
from althingi.updaters import update_parliament
from althingi.updaters import update_parties
from althingi.updaters import update_persons
from althingi.updaters import update_person
from althingi.updaters import update_sessions
from althingi.updaters import update_session
from althingi.updaters import update_speeches
from althingi.updaters import update_vote_casting
from althingi.updaters import update_vote_castings
from althingi.utils import get_last_parliament_num

from althingi.exceptions import AlthingiException

class Command(BaseCommand):

    help = 'Retrieves and saves parliamentary data from Althingi\'s XML feed.'

    def print_help(self):
        print 'Usage: python manage.py update_althingi <command> [options]'
        print
        print 'Commands:'
        print '  upcoming                          Update upcoming committee agendas and parliamentary sessions'
        print '  issues                            Update issues in default or specified parliament'
        print '  issue=<issue_num>                 Updates an issue by issue number'
        print '  sessions                          Updates sessions in default or specified parliament'
        print '  session=<session_num>             Updates a particular session by session number'
        print '  persons                           Updates persons (MPs) in default or specified parliament'
        print '  person=<person_xml_id>            Updates person by XML ID (see Althingi\'s XML)'
        print '  parties                           Updates parties in default or specified parliament'
        print '  committees                        Updates committees in default or specified parliament'
        print '  committee=<committee_xml_id>      Updates committee by XML ID (see Althingi\'s XML)'
        print '  committee_agendas                 Updates committee agendas in default or specified parliament'
        print '  committee_agenda=<agenda_xml_id>  Updates committee agenda by XML ID (see Althingi\'s XML)'
        print '  constituencies                    Updates constituencies in default or specified parliament'
        print '  vote_castings                     Updates vote castings in default or specified parliament'
        print '  vote_casting=<casting_xml_id>     Updates vote casting by XML ID (see Althingi\'s XML)'
        print '  speeches                          Updates speeches in default or specified parliament'
        print '  all                               Updates issues, sessions, persons, parties, constituencies and committee agendas in default or specified parliament'
        print
        print 'Options:'
        print '  parliament=<parliament_num>       Specify parliament number (defaults to current)'
        print '                                    Must be integer or range of integers, for example 130-140'
        print

    def error(self, msg, show_help=True):
        print u'Error: %s' % msg
        print
        if show_help:
            self.print_help()
        quit(2)

    def process_args(self, args):
        processed_args = {}
        for arg in args:
            if '=' in arg:
                try:
                    varname, varvalue = arg.split('=')
                except ValueError:
                    self.error('Argument "%s" is invalid' % arg)
            else:
                varname = arg
                varvalue = None

            processed_args[varname] = varvalue

        return processed_args

    def add_arguments(self, parser):
        parser.add_argument('arguments', nargs='+')

    def handle(self, *args, **options):
        try:
            processed_args = self.process_args(options['arguments'])

            if 'parliament' in processed_args:
                # If parliament is specified...
                try:
                    # Check if we want a range of parliaments.
                    if '-' in processed_args['parliament']:
                        from_to = processed_args['parliament'].split('-')
                        parliament_from = int(from_to[0])
                        parliament_to = int(from_to[1])
                    else:
                        parliament_from = parliament_to = int(processed_args['parliament'])
                except (TypeError, ValueError):
                    self.error('Invalid parliament number')
            else:
                # ...else, get the current one.
                parliament_from = parliament_to = get_last_parliament_num()

            # Determine order of iteration
            if parliament_from > parliament_to:
                iterator = reversed(xrange(parliament_to, parliament_from + 1))
            else:
                iterator = xrange(parliament_from, parliament_to + 1)

            for parliament_num in iterator:
                self.update_data(parliament_num, processed_args)

        except KeyboardInterrupt:
            quit(1)

    def update_data(self, parliament_num, args):

        print 'Processing parliament %d with args: %s' % (parliament_num, args)

        try:
            has_run = False
            if 'parliament' in args:
                has_run = True
                update_parliament(parliament_num)

            if 'parties' in args:
                has_run = True
                update_parties(parliament_num)

            if 'constituencies' in args:
                has_run = True
                update_constituencies(parliament_num)

            if 'persons' in args:
                has_run = True
                update_persons(parliament_num)

            if 'person' in args:
                has_run = True
                try:
                    person_xml_id = int(args['person'])
                except (TypeError, ValueError):
                    self.error('Invalid person XML-ID')
                update_person(person_xml_id, parliament_num)

            if 'issues' in args:
                has_run = True
                update_issues(parliament_num)

            if 'issue' in args:
                has_run = True
                try:
                    issue_num = int(args['issue'])
                except (TypeError, ValueError):
                    self.error('Invalid issue number')
                update_issue(issue_num, parliament_num)

            if 'sessions' in args:
                has_run = True
                update_sessions(parliament_num)

            if 'session' in args:
                has_run = True
                try:
                    session_num = int(args['session'])
                except (TypeError, ValueError):
                    self.error('Invalid session number')
                update_session(session_num, parliament_num)

            if 'committee' in args:
                has_run = True
                try:
                    committee_xml_id = int(args['committee'])
                except (TypeError, ValueError):
                    self.error('Invalid committee XML-ID')
                update_committee(committee_xml_id)

            if 'committees' in args:
                has_run = True
                update_committees(parliament_num)

            if 'committee_agendas' in args:
                has_run = True
                update_committee_agendas(parliament_num)

            if 'committee_agenda' in args:
                has_run = True
                try:
                    agenda_xml_id = int(args['committee_agenda'])
                except (TypeError, ValueError):
                    self.error('Invalid committee agenda XML-ID')
                update_committee_agenda(agenda_xml_id, parliament_num)

            if 'vote_castings' in args:
                has_run = True
                update_vote_castings(parliament_num)

            if 'vote_casting' in args:
                has_run = True
                try:
                    vote_casting_xml_id = int(args['vote_casting'])
                except (TypeError, ValueError):
                    self.error('Invalid vote casting XML-ID')
                update_vote_casting(vote_casting_xml_id)

            if 'speeches' in args:
                has_run = True
                update_speeches(parliament_num)

            if 'upcoming' in args:
                has_run = True
                update_next_sessions()
                update_next_committee_agendas()

            if 'all' in args:
                has_run = True
                update_parties(parliament_num)
                update_constituencies(parliament_num)
                update_committees(parliament_num)
                update_persons(parliament_num)
                update_issues(parliament_num)
                update_sessions(parliament_num)
                update_speeches(parliament_num)
                update_committee_agendas(parliament_num)
                update_vote_castings(parliament_num)

                # Mark parliament as fully updated.
                parliament = Parliament.objects.get(parliament_num=parliament_num)
                parliament.last_full_update = timezone.now()
                parliament.save()

        except AlthingiException as e:
            self.error(e)

        if not has_run:
            self.print_help()

