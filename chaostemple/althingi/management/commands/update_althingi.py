
from django.core.management.base import BaseCommand

from althingi.updaters import update_committee
from althingi.updaters import update_committee_agenda
from althingi.updaters import update_committee_agendas
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

from althingi.exceptions import AlthingiException

from datetime import datetime

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
        print '  committee=<committee_xml_id>      Updates committee by XML ID (see Althingi\'s XML)'
        print '  committee_agendas                 Updates committee agendas in default or specified parliament'
        print '  committee_agenda=<agenda_xml_id>  Updates committee agenda by XML ID (see Althingi\'s XML)'
        print '  constituencies                    Updates constituencies in default or specified parliament'
        print '  all                               Updates issues, sessions, persons, parties, constituencies and committee agendas in default or specified parliament'
        print
        print 'Options:'
        print '  parliament=<parliament_num>       Specify parliament number (defaults to current)'
        print

    def error(self, msg):
        print 'Error: %s' % msg
        print
        self.print_help()
        quit(2)

    def process_args(self, args):
        processed_args = {}
        for arg in args:
            if '=' in arg:
                varname, varvalue = arg.split('=')
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
            self.update_data(processed_args)
        except KeyboardInterrupt:
            quit(1)

    def update_data(self, args):

        parliament_num = None
        if 'parliament' in args:
            try:
                parliament_num = int(args['parliament'])
            except (TypeError, ValueError):
                self.error('Invalid parliament number')

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

            if 'committee_agendas' in args:
                has_run = True
                update_committee_agendas(parliament_num)

            if 'committee_agenda' in args:
                has_run = True
                try:
                    agenda_xml_id = int(args['committee_agenda'])
                except (TypeError, ValueError):
                    self.error('Invalid committee XML-ID')
                update_committee_agenda(agenda_xml_id, parliament_num)

            if 'upcoming' in args:
                has_run = True
                update_next_sessions()
                update_next_committee_agendas()

            if 'all' in args:
                has_run = True
                update_parties(parliament_num)
                update_constituencies(parliament_num)
                update_persons(parliament_num)
                update_issues(parliament_num)
                update_sessions(parliament_num)
                update_committee_agendas(parliament_num)
        except AlthingiException as e:
            self.error(e)

        if not has_run:
            self.print_help()

