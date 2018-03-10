from django.contrib import admin
from althingi.models import Parliament, Issue, Document


class ParliamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'parliament_num')


class IssueAdmin(admin.ModelAdmin):
    list_display = ('name', 'issue_num', 'issue_type', 'description',
                    'parliament')


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_num', 'doc_type', 'time_published', 'is_main',
                    'html_remote_path', 'pdf_remote_path', 'xhtml')


admin.site.register(Parliament, ParliamentAdmin)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Document, DocumentAdmin)
