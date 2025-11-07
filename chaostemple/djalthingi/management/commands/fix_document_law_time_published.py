from django.core.management.base import BaseCommand
from djalthingi.models import Document
from time import sleep


class Command(BaseCommand):

    help = "Fixes law documents so that they have the proper publishing date."

    def handle(self, *args, **options):
        try:
            law_docs = Document.objects.select_related(
                "issue",
                "issue__parliament"
            ).filter(
                is_law=True
            )
            for law_doc in law_docs:
                changed = law_doc.generate_law_metadata()
                changed = changed or law_doc.generate_html_content()

                if changed:
                    print(
                        "Saving doc nr. %d (issue nr. %s/%s)..." % (
                            law_doc.doc_num,
                            law_doc.issue.issue_num,
                            law_doc.issue.parliament.parliament_num
                        ),
                        end="",
                        flush=True
                    )
                    law_doc.save()
                    print(" done")

        except KeyboardInterrupt:
            quit(1)
