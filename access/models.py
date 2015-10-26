# encoding: utf-8

import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group

import requests
from requests.exceptions import HTTPError

from core.utils import get_code, SLUG_FIELD_PARAMS
from core.models import Person, Event, Organization


logger = logging.getLogger('kompassi')

STATE_CHOICES = [
    ('pending', u'Odottaa hyväksyntää'),
    ('approved', u'Hyväksytty, odottaa toteutusta'),
    ('granted', u'Myönnetty'),
    ('rejected', u'Hylätty'),
]
STATE_CSS = dict(
    pending='label-warning',
    approved='label-primary',
    granted='label-success',
    rejected='label-danger',
)


class Privilege(models.Model):
    slug = models.CharField(**SLUG_FIELD_PARAMS)
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    request_success_message = models.TextField(blank=True)

    grant_code = models.CharField(max_length=256)

    def grant(self, person):
        gp, created = GrantedPrivilege.objects.get_or_create(
            privilege=self,
            person=person,
            defaults=dict(
                state='approved'
            )
        )

        if gp.state != 'approved':
            return

        if 'background_tasks' in settings.INSTALLED_APPS:
            from .tasks import grant_privilege
            grant_privilege.delay(self.pk, person.pk)
        else:
            self._grant(person)

    def _grant(self, person):
        gp = GrantedPrivilege.objects.get(privilege=self, person=person, state='approved')

        grant_function = get_code(self.grant_code)
        grant_function(self, person)

        gp.state = 'granted'
        gp.save()

    @classmethod
    def get_potential_privileges(cls, person, **extra_criteria):
        assert person.user is not None
        return cls.objects.filter(
            group_privileges__group__in=person.user.groups.all(),
            **extra_criteria
        ).exclude(granted_privileges__person=person)

    def get_absolute_url(self):
        return u'{base_url}#privilege-{id}'.format(
            base_url=reverse('access_profile_privileges_view'),
            id=self.id,
        )

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = u'Käyttöoikeus'
        verbose_name_plural = u'Käyttöoikeudet'


class GroupPrivilege(models.Model):
    privilege = models.ForeignKey(Privilege, related_name='group_privileges')
    group = models.ForeignKey(Group, related_name='group_privileges')
    event = models.ForeignKey(Event, null=True, blank=True, related_name='group_privileges')

    def __unicode__(self):
        return u'{group_name} - {privilege_title}'.format(
            group_name=self.group.name if self.group else None,
            privilege_title=self.privilege.title if self.privilege else None,
        )

    class Meta:
        verbose_name = u'Ryhmän käyttöoikeus'
        verbose_name_plural = u'Ryhmien käyttöoikeudet'

        unique_together = [('privilege', 'group')]


class GrantedPrivilege(models.Model):
    privilege = models.ForeignKey(Privilege, related_name='granted_privileges')
    person = models.ForeignKey(Person, related_name='granted_privileges')
    state = models.CharField(default='granted', max_length=8, choices=STATE_CHOICES)

    granted_at = models.DateTimeField(auto_now_add=True)

    @property
    def state_css(self):
        return STATE_CSS[self.state]

    def __unicode__(self):
        return u'{person_name} - {privilege_title}'.format(
            person_name=self.person.full_name if self.person else None,
            privilege_title=self.privilege.title if self.privilege else None,
        )

    class Meta:
        verbose_name = u'Myönnetty käyttöoikeus'
        verbose_name_plural = u'Myönnetyt käyttöoikeudet'

        unique_together = [('privilege', 'person')]


class SlackError(RuntimeError):
    pass


class SlackAccess(models.Model):
    privilege = models.OneToOneField(Privilege, related_name='slack_access')
    team_name = models.CharField(max_length=255, verbose_name=u'Slack-yhteisön nimi')
    api_token = models.CharField(max_length=255, default=u'test', verbose_name=u'API-koodi')

    @property
    def invite_url(self):
        return 'https://{team_name}.slack.com/api/users.admin.invite'.format(team_name=self.team_name)

    def grant(self, person):
        if self.api_token == 'test':
            logger.warn(u'Using test mode for SlackAccess Privileges. No invites are actually being sent. '
                u'Would invite {name_and_email} to Slack if an actual API token were set.'.format(
                    name_and_email=person.name_and_email,
                )
            )
            return

        try:
            response = requests.get(self.invite_url, params=dict(
                token=self.api_token,
                email=person.email,
                first_name=person.first_name,
                last_name=person.surname,
                set_active=True,
            ))

            response.raise_for_status()
            result = response.json()

            if not result.get('ok'):
                raise SlackError(result)

            return result
        except (HTTPError, KeyError, IndexError, ValueError) as e:
            unused, unused, trace = sys.exc_info()
            raise SlackError(e), None, trace

    class Meta:
        verbose_name = u'Slack-kutsuautomaatti'
        verbose_name_plural = u'Slack-kutsuautomaatit'


class EmailAliasDomain(models.Model):
    domain_name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=u'Verkkotunnus',
        help_text=u'Esim. example.com'
    )
    organization = models.ForeignKey(Organization, verbose_name=u'Organisaatio')

    @classmethod
    def get_or_create_dummy(cls, domain_name='example.com'):
        organization, unused = Organization.get_or_create_dummy()

        return cls.objects.get_or_create(domain_name=domain_name, defaults=dict(organization=organization))

    def __unicode__(self):
        return self.domain_name

    class Meta:
        verbose_name = u'Verkkotunnus'
        verbose_name_plural = u'Verkkotunnukset'



class EmailAliasType(models.Model):
    domain = models.ForeignKey(EmailAliasDomain, verbose_name=u'Verkkotunnus')
    metavar = models.CharField(
        max_length=255,
        default=u'etunimi.sukunimi',
        verbose_name=u'Metamuuttuja',
        help_text=u'Esim. "etunimi.sukunimi"',
    )
    account_name_code = models.CharField(max_length=255, default='access.email_aliases:firstname_surname')

    def _make_account_name_for_person(self, person):
        account_name_func = get_code(self.account_name_code)
        return account_name_func(person)

    @classmethod
    def get_or_create_dummy(cls):
        domain, unused = EmailAliasDomain.get_or_create_dummy()
        return cls.objects.get_or_create(domain=domain)

    def admin_get_organization(self):
        return self.domain.organization if self.domain else None
    admin_get_organization.short_description = u'Organisaatio'
    admin_get_organization.admin_order_field = 'domain__organization'

    def __unicode__(self):
        return u'{metavar}@{domain}'.format(
            metavar=self.metavar,
            domain=self.domain.domain_name if self.domain else None,
        )

    class Meta:
        verbose_name = u'Sähköpostialiaksen tyyppi'
        verbose_name_plural = u'Sähköpostialiasten tyypit'


class GroupEmailAliasGrant(models.Model):
    group = models.ForeignKey(Group, verbose_name=u'Ryhmä')
    type = models.ForeignKey(EmailAliasType, verbose_name=u'Tyyppi')

    def __unicode__(self):
        return self.group.name

    class Meta:
        verbose_name = u'Myöntämiskanava'
        verbose_name_plural = u'Myöntämiskanavat'


class EmailAlias(models.Model):
    type = models.ForeignKey(EmailAliasType, verbose_name=u'Tyyppi')
    person = models.ForeignKey(Person, verbose_name=u'Henkilö', related_name='email_aliases')
    account_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=u'Tunnus',
        help_text=u'Ennen @-merkkiä tuleva osa sähköpostiosoitetta. Muodostetaan automaattisesti jos tyhjä.',
    )

    # denormalized to facilitate searching etc
    email_address = models.CharField(
        max_length=511,
        verbose_name=u'Sähköpostiosoite',
        help_text=u'Muodostetaan automaattisesti',
    )

    # to facilitate easy pruning of old addresses
    group_grant = models.ForeignKey(GroupEmailAliasGrant,
        blank=True,
        null=True,
        verbose_name=u'Myöntämiskanava',
        help_text=u'Myöntämiskanava antaa kaikille tietyn ryhmän jäsenille tietyntyyppisen sähköpostialiaksen. '
            u'Jos aliakselle on asetettu myöntämiskanava, alias on myönnetty tämän myöntämiskanavan perusteella, '
            u'ja kun myöntämiskanava vanhenee, kaikki sen perusteella myönnetyt aliakset voidaan poistaa kerralla.'
    )

    # denormalized, for unique_together and easy queries
    domain = models.ForeignKey(EmailAliasDomain, verbose_name=u'Verkkotunnus')

    def _make_email_address(self):
        return u'{account_name}@{domain}'.format(
            account_name=self.account_name,
            domain=self.domain.domain_name,
        ) if self.account_name and self.domain else None

    @classmethod
    def get_or_create_dummy(cls):
        alias_type, unused = EmailAliasType.get_or_create_dummy()
        person, unused = Person.get_or_create_dummy()

        return cls.objects.get_or_create(
            type=alias_type,
            person=person,
        )

    def admin_get_organization(self):
        return self.type.domain.organization if self.type else None
    admin_get_organization.short_description = u'Organisaatio'
    admin_get_organization.admin_order_field = 'type__domain__organization'

    def __unicode__(self):
        return self.email_address

    class Meta:
        verbose_name = u'Sähköpostialias'
        verbose_name_plural = u'Sähköpostialiakset'

        unique_together = [('domain', 'account_name')]


@receiver(pre_save, sender=EmailAlias)
def populate_email_alias_computed_fields(sender, instance, **kwargs):
    if instance.type:
        instance.domain = instance.type.domain

        if instance.person and not instance.account_name:
            instance.account_name = instance.type._make_account_name_for_person(instance.person)

        if instance.account_name:
            instance.email_address = instance._make_email_address()
