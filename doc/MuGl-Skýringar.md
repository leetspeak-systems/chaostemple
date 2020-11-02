# Þróunarumhverfi

* Python 3.x
* [Django](https://www.djangoproject.com/) 2.2.x.
* [Bootstrap](https://getbootstrap.com/) 3.3.7

# Gagnagrunnur

Notast er við [Object-Relational Mapping (ORM) í Django](https://docs.djangoproject.com/en/2.2/topics/db/models/), en undirliggjandi gagnagrunnurinn sem notaður er í dag, er [MySQL](https://www.mysql.com/).

# Hlutar

Á Django-máli eru aðskildir hlutar kallaðir hinu ruglandi nafni „apps“. Hér verður fjallað um þá sem „hluta“ á íslensku og eru þeir í stafrófsröð.

## chaostemple

Inngangspunktur forritsins, sem vísar notandanum og þróunarumhverfi á vit hinna hlutanna.

## core

Inniheldur þá virkni sem tilheyrir grunnvirkni forritsins sjálfs eða er erfitt að afmarka við tiltekið hlutverk. Hér er t.d. geymd aðgangsstjórnun, beiðnir um aðgang að þingflokkum, virkni sem varðar vaktanir mála, notendamál og fleira slíkt.

## customsignup

Sérskrifaður nýskráningarhluti til þess að gera notendum með @althingi.is netfang að skrá sig einungis með netfangi, án notandanafns, sem og til að kerfið geti borið kennsl á þingmenn sem nýskrá sig. Þannig getur kerfið t.d. sett þingmenn í sama þingflokki í sama hóp og gefið þeim sjálfkrafa aðgang að gögnum hvors annars án þess að þeir hafi aðgang að gögnum annarra þingflokka.

## djalthingi

Sjálfstæður hluti, sem ætti í rauninni að vera aðskilið verkefni, en hann sér alfarið um að sækja, greina og skipuleggja gögn sem sótt eru frá Alþingi og sett í gagnagrunn.

Þessi hluti er sérstakur að því leyti að hann er með sína eigin stillingaskrá, undir `djalthingi/althingi_settings.py`. Er það hugsað til þess að auðvelt sé að aðskilja hann frá heildarverkefninu og nota í öðrum verkefnum sem þurfa að meðhöndla gögn Alþingis.

Gögn til Alþingis eru sótt með skipuninni `./manage.py update_althingi <options>` og þarf að keyra nokkrar mismunandi slíkar skipanir reglulega til þess að halda gögnunum ferskum. Hægt er að ná í öll gögn líðandi þings, en einnig að velja sérstök gögn, t.d. ræður eða atkvæðagreiðslur, þingmenn eða þingmál. Jafnvel er hægt að sækja gögn um einstaka þingmál eða þingmenn einungis. Í eintakinu sem nú keyrir er náð í öll gögn einu sinni á sólarhring (að nóttu til), en atkvæðagreiðslur, ræður og mál á næstunni (á dagskrá nefnda eða þingfunda) sótt oftar, eftir því hversu fersk gögnin þurfa að vera fyrir tiltekna virkni forritsins. Ræður og atkvæðagreiðslur eru sóttar mjög oft til þess að reikna út stöðu mála (t.d. „komið úr nefnd“ eða „bíður 3. umræðu“).

## dossier

Inniheldur svokallaðar greiningar og tengist þingmálum með skjölum (s.k. A-málum).

Þegar glósur eru skrifaðar fyrir þingskjal, eða staða þess eða eðli merkt með öðrum hætti, er það geymt í svokölluðum `dossier`. Þetta er því lykilatriði í virkni forritsins. Einn `dossier` er tengdur ýmist við þingskjal eða umsögn, og fara möguleikarnir sem `dossier` býður upp á eftir eðli skjalsins. Þannig er t.d. hægt að merkja stuðning umsagnar eða nefndarálits við þingmál, en ekki stuðning frumvarps, þar sem það er órökrétt að tala um að frumvarp styðji sjálft sig.

Einnig er haldið utan um `DossierStatistic` sem tengist málum (og mál samanstanda af þingskjölum og umsögnum). Þar eru settar heildarupplýsingar um t.d. fjölda greininga, hversu margar umsagnir hafa verið lesnar af notandanum og þess háttar. Líta má á `DossierStatistic` sem einskonar samantekt af `Dossier`.

## jsonizer

Sjálfstæður hluti sem sér um JSON-samskipti við netþjón. Inniheldur kóða bæði fyrir netþjón (Python) og vafra (JavaScript) til að straumlínulaga JSON-samskipti.

## locale

Er reyndar ekki Django app, heldur inniheldur þýðingar á íslensku. Forritið er allt skrifað á ensku, sem veldur stundum klaufalegu orðavali yfir hluti sem jafnan er einungis talað um á íslensku. Texti er síðan þýddur fyrir notandann.

Þannig er í sjálfu sér hægt að setja upp forritið á ensku eða þýða það yfir á önnur mál, en gögnin frá Alþingi eru hinsvegar öll á íslensku, t.d. nöfn þingflokka, nöfn mála og þess háttar.

## templates

Inniheldur HTML skjöl fyrir notendaviðmótið. Template-málið er mjög dæmigert fyrir nútíma template-mál eins og Liquid, sem er víða notað, t.d. í Jekyll og fleiri vefþróunartólum.
