from django.core.management.base import BaseCommand
from os import walk
from PyPDF2 import PdfFileReader


class Command(BaseCommand):
    """
    Counts downloaded PDF files and their pages.
    """

    def handle(self, *args, **options):

        file_count = 0
        page_count = 0
        for dirpath, dirnames, filenames in walk("althingi/static/althingi"):
            files = ["%s/%s" % (dirpath, name) for name in filenames]
            for filename in files:
                if filename[-4:] != ".pdf":
                    continue

                reader = PdfFileReader(filename)

                page_count += reader.getNumPages()
                file_count += 1

                print(".", end="", flush=True)

        print()
        print("Number of files: %d" % file_count)
        print("Number of pages: %d" % page_count)
