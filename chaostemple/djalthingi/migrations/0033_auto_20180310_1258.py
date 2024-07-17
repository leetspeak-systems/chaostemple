# Generated by Django 2.0.3 on 2018-03-10 12:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0032_auto_20180302_1959"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="doc_type",
            field=models.CharField(
                choices=[
                    ("álit nefndar um skýrslu", "álit nefndar um skýrslu"),
                    ("beiðni um skýrslu", "beiðni um skýrslu"),
                    ("breytingartillaga", "breytingartillaga"),
                    ("framhaldsnefndarálit", "framhaldsnefndarálit"),
                    ("frávísunartilllaga", "frávísunartilllaga"),
                    ("frestun funda", "frestun funda"),
                    ("frumvarp", "frumvarp"),
                    ("frhnál. með brtt.", "framhaldsnefndarálit með breytingartillögu"),
                    (
                        "frhnál. með frávt.",
                        "framhaldsnefndarálit með frávísunartillögu",
                    ),
                    ("frhnál. með rökst.", "framhaldsnefndarálit með rökstuðningi"),
                    ("frumvarp eftir 2. umræðu", "frumvarp eftir 2. umræðu"),
                    ("frumvarp nefndar", "frumvarp nefndar"),
                    ("frv. til. stjórnarsk.", "frumvarp til stjórnarskrár"),
                    ("fsp. til munnl. svars", "fyrirspurn til munnlegs svars"),
                    ("fsp. til skrifl. svars", "fyrirspurn til skriflegs svars"),
                    ("lög (m.áo.br.)", "lög (með áorðnum breytingum"),
                    ("lög (samhlj.)", "lög (samhljóða)"),
                    ("lög í heild", "lög í heild"),
                    ("nál. með brtt.", "nefndarálit með breytingartillögu"),
                    ("nál. með frávt.", "nefndarálit með frávísunartillögu"),
                    ("nál. með rökst.", "nefndarálit með rökstuðningi"),
                    ("nefndarálit", "nefndarálit"),
                    ("rökstudd dagskrá", "rökstudd dagskrá"),
                    ("skýrsla (skv. beiðni)", "skýrsla (samkvæmt beiðni)"),
                    ("skýrsla n.", "skýrsla nefndar"),
                    ("skýrsla n. (frumskjal)", "skýrsla nefndar (frumskjal)"),
                    ("skýrsla rh. (frumskjal)", "skýrsla ráðherra (frumskjal)"),
                    ("stjórnarfrumvarp", "stjórnarfrumvarp"),
                    ("stjórnartillaga", "stjórnartillaga"),
                    ("svar", "svar"),
                    ("vantraust", "vantraust"),
                    ("þál. (samhlj.)", "þingsályktunartillaga (samhljóða)"),
                    ("þál. í heild", "þingsályktunartillaga í heild"),
                    ("þáltill.", "þingsályktunartillaga"),
                    ("þáltill. n.", "þingsályktunartillaga nefndar"),
                ],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="current_step",
            field=models.CharField(
                choices=[
                    ("distributed", "Distributed"),
                    ("iteration-1-waiting", "Awaiting 1st debate"),
                    ("iteration-1-current", "Currently in 1st debate"),
                    ("iteration-1-finished", "1st debate concluded"),
                    ("committee-1-waiting", "Sent to committee"),
                    ("committee-1-current", "Currently in committee"),
                    ("committee-1-finished", "Considered by committee"),
                    ("iteration-2-waiting", "Awaiting 2nd debate"),
                    ("iteration-2-current", "Currently in 2nd debate"),
                    ("iteration-2-finished", "2nd debate concluded"),
                    ("committee-2-waiting", "Sent to committee (after 2nd debate)"),
                    (
                        "committee-2-current",
                        "Currently in committee (after 2nd debate)",
                    ),
                    (
                        "committee-2-finished",
                        "Considered by committee (after 2nd debate)",
                    ),
                    ("iteration-3-waiting", "Awaiting 3rd debate"),
                    ("iteration-3-current", "Currently in 3rd debate"),
                    ("iteration-3-finished", "3rd debate concluded"),
                    ("concluded", "Issue concluded"),
                    ("distributed", "Distributed"),
                    ("iteration-former-waiting", "Awaiting former debate"),
                    ("iteration-former-current", "Currently in former debate"),
                    ("iteration-former-finished", "Former debate concluded"),
                    ("committee-former-waiting", "Sent to committee"),
                    ("committee-former-current", "Currently in committee"),
                    ("committee-former-finished", "Considered by committee"),
                    ("iteration-latter-waiting", "Awaiting latter debate"),
                    ("iteration-latter-current", "Currently in latter debate"),
                    ("iteration-latter-finished", "Latter debate concluded"),
                    ("concluded", "Issue concluded"),
                    ("distributed", "Distributed"),
                    ("answered", "Answered"),
                    ("distributed", "Distributed"),
                    ("voted-on", "Voted on"),
                    ("report-delivered", "Report delieverd"),
                    ("concluded", "Concluded"),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="fate",
            field=models.CharField(
                choices=[
                    ("rejected", "rejected"),
                    ("accepted", "accepted"),
                    ("sent-to-government", "sent to government"),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="issue_group",
            field=models.CharField(
                choices=[
                    ("A", "þingmál með þingskjölum"),
                    ("B", "þingmál án þingskjala"),
                ],
                default="A",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="committee",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="djalthingi.Committee",
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="president_seat",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="djalthingi.PresidentSeat",
            ),
        ),
        migrations.AlterField(
            model_name="review",
            name="sender_name_description",
            field=models.CharField(default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="seat",
            name="name_abbreviation",
            field=models.CharField(default="", max_length=15),
        ),
        migrations.AlterField(
            model_name="sessionagendaitem",
            name="discussion_type",
            field=models.CharField(
                choices=[
                    ("*", ""),
                    ("0", ""),
                    ("1", "1. umræða"),
                    ("2", "2. umræða"),
                    ("3", "3. umræða"),
                    ("E", "ein umræða"),
                    ("F", "fyrri umræða"),
                    ("S", "síðari umræða"),
                ],
                max_length=1,
            ),
        ),
    ]
