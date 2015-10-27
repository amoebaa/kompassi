# encoding: utf-8

import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, make_option
from django.utils.timezone import now

from dateutil.tz import tzlocal

from core.utils import slugify


def mkpath(*parts):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', *parts))


class Setup(object):
    def __init__(self):
        self._ordering = 0

    def get_ordering_number(self):
        self._ordering += 10
        return self._ordering

    def setup(self, test=False):
        self.test = test
        self.tz = tzlocal()
        self.setup_core()
        self.setup_labour()
        # self.setup_tickets()
        self.setup_access()
        # self.setup_payments()

    def setup_core(self):
        from core.models import Venue, Event, Organization

        self.organization = Organization.objects.get(slug='aicon-ry')
        self.venue, unused = Venue.objects.get_or_create(
            name='Verkatehdas',
            name_inessive='Verkatehtaalla',
        )
        self.event, unused = Event.objects.get_or_create(slug='aicon2016', defaults=dict(
            name='Aicon',
            name_genitive='Aiconin',
            name_illative='Aiconiin',
            name_inessive='Aiconissa',
            homepage_url='http://2016.aicon.fi',
            organization=self.organization,
            start_time=datetime(2016, 10, 8, 10, 0, tzinfo=self.tz),
            end_time=datetime(2016, 10, 9, 18, 0, tzinfo=self.tz),
            venue=self.venue,
        ))

    def setup_labour(self):
        from core.models import Person
        from labour.models import (
            AlternativeSignupForm,
            InfoLink,
            Job,
            JobCategory,
            LabourEventMeta,
            Perk,
            PersonnelClass,
            Qualification,
            WorkPeriod,
        )
        from ...models import SignupExtra, SpecialDiet
        from django.contrib.auth.models import Group
        from django.contrib.contenttypes.models import ContentType

        labour_admin_group, created = Group.objects.get_or_create(name='aicon-staff')

        if self.test and created:
            person, unused = Person.get_or_create_dummy()
            labour_admin_group.user_set.add(person.user)

        content_type = ContentType.objects.get_for_model(SignupExtra)

        labour_event_meta_defaults = dict(
            signup_extra_content_type=content_type,
            work_begins=datetime(2016, 10, 7, 8, 0, tzinfo=self.tz),
            work_ends=datetime(2016, 10, 9, 22, 0, tzinfo=self.tz),
            admin_group=labour_admin_group,
            contact_email='Aicon-työvoimatiimi <tyovoima@aicon.fi>',
        )

        if self.test:
            t = now()
            labour_event_meta_defaults.update(
                registration_opens=t - timedelta(days=60),
                registration_closes=t + timedelta(days=60),
            )
        else:
            # TODO once we know when the registration opens
            # labour_event_meta_defaults.update(
            #     registration_opens=datetime(2014, 3, 1, 0, 0, tzinfo=self.tz),
            #     registration_closes=datetime(2014, 8, 1, 0, 0, tzinfo=self.tz),
            # )
            pass

        labour_event_meta, unused = LabourEventMeta.objects.get_or_create(
            event=self.event,
            defaults=labour_event_meta_defaults,
        )

        for pc_name, pc_slug, pc_app_label in [
            (u'Vastaava', 'vastaava', 'labour'),
            # (u'Vuorovastaava', 'ylivankari', 'labour', True),
            # (u'Työvoima', 'tyovoima', 'labour', True),
            # (u'Ohjelmanjärjestäjä', 'ohjelma', 'programme', True),
            # (u'Guest of Honour', 'goh', 'programme', False), # tervetullut muttei kutsuta automaattiviestillä
            # (u'Media', 'media', 'badges', False),
            # (u'Myyjä', 'myyja', 'badges', False),
            # (u'Vieras', 'vieras', 'badges', False),
        ]:
            personnel_class, created = PersonnelClass.objects.get_or_create(
                event=self.event,
                slug=pc_slug,
                defaults=dict(
                    name=pc_name,
                    app_label=pc_app_label,
                    priority=self.get_ordering_number(),
                ),
            )

        # tyovoima = PersonnelClass.objects.get(event=self.event, slug='tyovoima')
        vastaava = PersonnelClass.objects.get(event=self.event, slug='vastaava')
        # ylivankari = PersonnelClass.objects.get(event=self.event, slug='ylivankari')
        # ohjelma = PersonnelClass.objects.get(event=self.event, slug='ohjelma')

        for jc_data in [
            (u'Vastaava', u'Tapahtuman järjestäjä', [vastaava]),

            # (u'Erikoistehtävä', u'Mikäli olet sopinut erikseen työtehtävistä ja/tai sinut on ohjeistettu täyttämään lomake, valitse tämä ja kerro tarkemmin Vapaa alue -kentässä mihin tehtävään ja kenen toimesta sinut on valittu.', [tyovoima, ylivankari]),
            # (u'Järjestyksenvalvoja', u'Kävijöiden turvallisuuden valvominen conipaikalla ja yömajoituksessa. Edellyttää voimassa olevaa JV-korttia ja asiakaspalveluasennetta. HUOM! Et voi valita tätä tehtävää hakemukseesi, ellet ole täyttänyt tietoihisi JV-kortin numeroa (oikealta ylhäältä oma nimesi &gt; Pätevyydet).', [tyovoima, ylivankari]),
            # (u'Ensiapu', 'Toimit osana tapahtuman omaa ensiapuryhmää. Vuoroja päivisin ja öisin tapahtuman aukioloaikoina. Vaaditaan vähintään voimassa oleva EA1 -kortti ja osalta myös voimassa oleva EA2 -kortti. Kerro Työkokemus -kohdassa osaamisestasi, esim. oletko toiminut EA-tehtävissä tapahtumissa tai oletko sairaanhoitaja/lähihoitaja koulutuksestaltasi.', [tyovoima, ylivankari]),
            # (u'Kasaus ja purku', u'Kalusteiden siirtelyä & opasteiden kiinnittämistä. Ei vaadi erikoisosaamista. Työvuoroja myös jo pe sekä su conin sulkeuduttua, kerro lisätiedoissa jos voit osallistua näihin.', [tyovoima, ylivankari]),
            # (u'Logistiikka', u'Autokuskina toimimista ja tavaroiden/ihmisten hakua ja noutamista. B-luokan ajokortti vaaditaan. Työvuoroja myös perjantaille.', [tyovoima, ylivankari]),
            # (u'Majoitusvalvoja', u'Huolehtivat lattiamajoituspaikkojen pyörittämisestä yöaikaan. Työvuoroja myös molempina öinä.', [tyovoima, ylivankari]),
            # (u'myynti', u'Lipunmyynti ja narikka', u'Pääsylippujen ja Tracon-oheistuotteiden myyntiä sekä lippujen tarkastamista. Myyjiltä edellytetään täysi-ikäisyyttä, asiakaspalveluhenkeä ja huolellisuutta rahankäsittelyssä. Vuoroja myös perjantaina.', [tyovoima, ylivankari]),
            # (u'info', u'Info-, ohjelma- ja yleisvänkäri', u'Infopisteen henkilökunta vastaa kävijöiden kysymyksiin ja ratkaisee heidän ongelmiaan tapahtuman paikana. Tehtävä edellyttää asiakaspalveluasennetta, tervettä järkeä ja ongelmanratkaisukykyä.', [tyovoima, ylivankari]),

            # (u'Ohjelmanpitäjä', u'Luennon tai muun vaativan ohjelmanumeron pitäjä', [ohjelma]),
        ]:
            if len(jc_data) == 3:
                name, description, pcs = jc_data
                slug = slugify(name)
            elif len(jc_data) == 4:
                slug, name, description, pcs = jc_data

            job_category, created = JobCategory.objects.get_or_create(
                event=self.event,
                slug=slug,
                defaults=dict(
                    name=name,
                    description=description,
                )
            )

            if created:
                job_category.personnel_classes = pcs
                job_category.save()

        labour_event_meta.create_groups()

        for name in [u'Vastaava']:
            JobCategory.objects.filter(event=self.event, name=name).update(public=False)

        # for jc_name, qualification_name in [
        #     (u'Järjestyksenvalvoja', u'JV-kortti'),
        #     (u'Logistiikka', u'Henkilöauton ajokortti (B)'),
        # ]:
        #     jc = JobCategory.objects.get(event=self.event, name=jc_name)
        #     qual = Qualification.objects.get(name=qualification_name)

        for diet_name in [
            u'Gluteeniton',
            u'Laktoositon',
            u'Maidoton',
            u'Vegaaninen',
            u'Lakto-ovo-vegetaarinen',
        ]:
            SpecialDiet.objects.get_or_create(name=diet_name)

        AlternativeSignupForm.objects.get_or_create(
            event=self.event,
            slug=u'vastaava',
            defaults=dict(
                title=u'Vastaavien ilmoittautumislomake',
                signup_form_class_path='events.aicon2016.forms:OrganizerSignupForm',
                signup_extra_form_class_path='events.aicon2016.forms:OrganizerSignupExtraForm',
                active_from=datetime(2015, 10, 27, 12, 0, 0, tzinfo=self.tz),
                active_until=datetime(2016, 10, 9, 23, 59, 59, tzinfo=self.tz),
            ),
        )

        for wiki_space, link_title, link_group in [
            # ('AICONWORK', 'Työvoimawiki', 'accepted'),
            # ('AICONINFO', 'Infowiki', 'info'),
        ]:
            InfoLink.objects.get_or_create(
                event=self.event,
                title=link_title,
                defaults=dict(
                    url='https://confluence.tracon.fi/display/{wiki_space}'.format(wiki_space=wiki_space),
                    group=labour_event_meta.get_group(link_group),
                )
            )

    def setup_tickets(self):
        # XXX update for Aicon
        from tickets.models import TicketsEventMeta, LimitGroup, Product

        tickets_admin_group, unused = TicketsEventMeta.get_or_create_group(self.event, 'admins')

        defaults = dict(
            admin_group=tickets_admin_group,
            due_days=14,
            shipping_and_handling_cents=120,
            reference_number_template="2016{:05d}",
            contact_email='Aicon-lipunmyynti <liput@aicon.fi>',
            plain_contact_email='liput@aicon.fi',
            ticket_free_text=u"Tämä on sähköinen lippusi Aicon-tapahtumaan. Sähköinen lippu vaihdetaan rannekkeeseen\n"
                u"lipunvaihtopisteessä saapuessasi tapahtumaan. Voit tulostaa tämän lipun tai näyttää sen\n"
                u"älypuhelimen tai tablettitietokoneen näytöltä. Mikäli kumpikaan näistä ei ole mahdollista, ota ylös\n"
                u"kunkin viivakoodin alla oleva neljästä tai viidestä sanasta koostuva Kissakoodi ja ilmoita se\n"
                u"lipunvaihtopisteessä.\n\n"
                u"Tervetuloa Aiconin!",
            front_page_text=u"<h2>Tervetuloa ostamaan pääsylippuja Aicon-tapahtumaan!</h2>"
                u"<p>Liput maksetaan suomalaisilla verkkopankkitunnuksilla heti tilauksen yhteydessä.</p>"
                u"<p>Lue lisää tapahtumasta <a href='http://2016.aicon.fi'>Aicon-tapahtuman kotisivuilta</a>.</p>"
                u"<p>Huom! Tämä verkkokauppa palvelee ainoastaan asiakkaita, joilla on osoite Suomessa. Mikäli tarvitset "
                u"toimituksen ulkomaille, ole hyvä ja ota sähköpostitse yhteyttä: <em>liput@aicon.fi</em>"
        )

        if self.test:
            t = now()
            defaults.update(
                ticket_sales_starts=t - timedelta(days=60),
                ticket_sales_ends=t + timedelta(days=60),
            )
        else:
            # TODO
            # defaults.update(
            #     ticket_sales_starts=datetime(2016, 3, 4, 18, 0, tzinfo=self.tz),
            #     ticket_sales_ends=datetime(2016, 6, 28, 18, 0, tzinfo=self.tz),
            # )
            pass

        meta, unused = TicketsEventMeta.objects.get_or_create(event=self.event, defaults=defaults)

        def limit_group(description, limit):
            limit_group, unused = LimitGroup.objects.get_or_create(
                event=self.event,
                description=description,
                defaults=dict(limit=limit),
            )

            return limit_group

        for product_info in [
            dict(
                name=u'Aicon-pääsylippu',
                description=u'Viikonloppulippu Aicon-tapahtumaan. Voimassa koko viikonlopun ajan la klo 12 – su klo 18. Toimitetaan sähköpostitse PDF-tiedostona, jossa olevaa viivakoodia vastaan saat rannekkeen tapahtumaan saapuessasi.',
                limit_groups=[
                    limit_group('Pääsyliput', 400),
                ],
                price_cents=1000,
                requires_shipping=False,
                electronic_ticket=True,
                available=True,
                ordering=self.get_ordering_number(),
            ),
        ]:
            name = product_info.pop('name')
            limit_groups = product_info.pop('limit_groups')

            product, unused = Product.objects.get_or_create(
                event=self.event,
                name=name,
                defaults=product_info
            )

            if not product.limit_groups.exists():
                product.limit_groups = limit_groups
                product.save()

    def setup_access(self):
        from access.models import Privilege, GroupPrivilege, EmailAliasDomain, EmailAliasType, GroupEmailAliasGrant

        cc_group = self.event.labour_event_meta.get_group('vastaava')
        domain = EmailAliasDomain.objects.get(domain_name='aicon.fi')

        for type_code, type_metavar in [
            ('events.aicon2016.email_aliases:requested_alias', u'aicon11tehtävä'),
        ]:
            alias_type, created = EmailAliasType.objects.get_or_create(
                domain=domain,
                account_name_code=type_code,
                defaults=dict(
                    metavar=type_metavar,
                )
            )

        for metavar in [
            'etunimi.sukunimi',
            'nick',
            'aicon11tehtävä',
        ]:
            alias_type = EmailAliasType.objects.get(domain__domain_name='aicon.fi', metavar=metavar)
            GroupEmailAliasGrant.objects.get_or_create(
                group=cc_group,
                type=alias_type,
                defaults=dict(
                    active_until=self.event.end_time,
                )
            )

    def setup_payments(self):
        from payments.models import PaymentsEventMeta
        PaymentsEventMeta.get_or_create_dummy(event=self.event)


class Command(BaseCommand):
    args = ''
    help = 'Setup aicon2016 specific stuff'

    option_list = BaseCommand.option_list + (
        make_option('--test',
            action='store_true',
            dest='test',
            default=False,
            help='Set the event up for testing',
        ),
    )

    def handle(self, *args, **opts):
        Setup().setup(test=opts['test'])
