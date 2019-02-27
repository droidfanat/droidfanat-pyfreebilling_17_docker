# Copyright 2013 Mathias WOLFF
# This file is part of pyfreebilling.
#
# pyfreebilling is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfreebilling is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfreebilling.  If not, see <http://www.gnu.org/licenses/>

from django.db import models
from django.db.models import permalink, Sum, Avg, Count, Max, Min
from django.core.validators import EMPTY_VALUES
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html

import datetime
import qsstats
import vatnumber

import decimal

import math

from django_countries.fields import CountryField

from netaddr import IPNetwork, AddrFormatError

import re

from currencies.models import Currency

from pyfreebill.validators import validate_cidr

# CustomUser -- Django 1.6
# class CustomUser(AbstractUser):
#    keyboard_shortcuts = models.BooleanField(default=True)

# Finance
from django.core.exceptions import ValidationError


def check_vat(value):
    if value != "" and not vatnumber.check_vat(value):
        raise ValidationError(_(u"%s is not a valid VAT number") % value)


class Company(models.Model):
    """Company model."""
    name = models.CharField(_(u'name'),
                            max_length=200,
                            unique=True)
    nickname = models.CharField(_(u'nickname'),
                                max_length=50,
                                blank=True,
                                null=True)
    slug = models.SlugField(_(u'slug'),
                            max_length=50,
                            unique=True)
    about = models.CharField(_(u'about'),
                             max_length=250,
                             blank=True,
                             null=True)
    phone_number = GenericRelation(u'PhoneNumber')
    email_address = GenericRelation(u'EmailAddress')
    web_site = GenericRelation(u'WebSite')
    street_address = GenericRelation(u'StreetAddress')
    account_number = models.IntegerField(_(u"Account number"),
                                         blank=True,
                                         null=True)
    vat = models.BooleanField(_(u"VAT Applicable / Not applicable"),
                              default=False,
                              help_text=_(u"if checked, VAT is applicable."))
    vat_number = models.CharField(_(u"VAT number"),
                                  max_length=30,
                                  blank=True,
                                  validators=[check_vat])
    vat_number_validated = models.BooleanField(_(u"VAT Vies Validated."),
                                               default=False,
                                               help_text=_(u"If on, it means that VAT is "
                                                           u"validated through <a target='_blank' "
                                                           u"href='http://ec.europa.eu/taxation_customs/vies/vatRequest.html'>Vies</a>."))
    prepaid = models.BooleanField(_(u"Prepaid / Postpaid"),
                                  default=True,
                                  help_text=_(u"If checked, this account customer is prepaid."))
    credit_limit = models.DecimalField(_(u'credit limit'),
                                       max_digits=12,
                                       decimal_places=4,
                                       default=0,
                                       help_text=_(u"Credit limit for postpaid account."))
    low_credit_alert = models.DecimalField(_(u'low credit level alert'),
                                           max_digits=12,
                                           decimal_places=4,
                                           default="10",
                                           help_text=_(u"Low credit limit alert."))
    low_credit_alert_sent = models.BooleanField(_(u"low credit alert ON"),
                                                default=False)
    account_blocked_alert_sent = models.BooleanField(_(u"Customer account blocked - low balance - ON"),
                                                     default=False)
    email_alert = models.EmailField(_(u'alert email address'),
                                    blank=True,
                                    null=True)
    customer_balance = models.DecimalField(_(u'customer balance'),
                                           max_digits=12,
                                           decimal_places=6,
                                           default=0,
                                           help_text=_(u"Actual customer balance."))
    cb_currency = models.ForeignKey(Currency,
                                verbose_name=_(u"Currency"))
    supplier_balance = models.DecimalField(_(u'supplier balance'),
                                           max_digits=12,
                                           decimal_places=6,
                                           default=0,
                                           help_text=_(u"Actual supplier balance."))
    max_calls = models.PositiveIntegerField(_(u'max simultaneous calls'),
                                            default=1,
                                            help_text=_(u"maximum simultaneous calls allowed for this customer account."))
    calls_per_second = models.PositiveIntegerField(
        _(u'max calls per second'),
        default=10,
        help_text=_(u"maximum calls per seconds allowed for this customer account.")
    )
    BILLING_CYCLE_CHOICES = (
        ('w', _(u'weekly')),
        ('m', _(u'monthly')),
    )
    billing_cycle = models.CharField(
        _(u'billing cycle'),
        max_length=10,
        choices=BILLING_CYCLE_CHOICES,
        default='m',
        help_text=_(u"billinng cycle for invoice generation.")
    )
    customer_enabled = models.BooleanField(_(u"Customer Enabled / Disabled"),
                                           default=True)
    supplier_enabled = models.BooleanField(_(u"Supplier Enabled / Disabled"),
                                           default=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'company'
        ordering = ('name',)
        verbose_name = _(u"Company")
        verbose_name_plural = _(u"Companies")

    def clean(self):
        if self.vat_number:
            try:
                vatnumber.check_vies(self.vat_number)
            except Exception, e:
                raise ValidationError(_(u"""Wrong VAT number - validation made throw VIES services. %s""")) % e

    def save(self, *args, **kwargs):
        if self.vat_number:
            try:
                self.vat_number_validated = vatnumber.check_vies(self.vat_number)
            except:
                self.vat_number_validated = False
        else:
            self.vat_number_validated = False

        super(Company, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s" % self.name

    def colored_name(self):
        if self.customer_enabled == False and self.supplier_enabled == False:
            color = "red"
        elif self.customer_enabled == False and self.supplier_enabled == True:
            color = "orange"
        elif self.customer_enabled == True and self.supplier_enabled == False:
            color = "purple"
        else:
            color = "green"
        return " <span style=color:%s>%s</span>" % (color, self.name)
    colored_name.allow_tags = True

    def balance_history(self):
        html = '<span><a href="/extranet/pyfreebill/companybalancehistory/?company__id__exact={0}" class="btn btn-inverse btn-mini">Balance history <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.id))
    balance_history.allow_tags = True
    balance_history.short_description = _(u'balance history')


class Person(models.Model):
    """Person model."""
    first_name = models.CharField(_(u'first name'),
                                  max_length=100)
    last_name = models.CharField(_(u'last name'),
                                 max_length=200)
    middle_name = models.CharField(_(u'middle name'),
                                   max_length=200,
                                   blank=True,
                                   null=True)
    suffix = models.CharField(_(u'suffix'),
                              max_length=50,
                              blank=True,
                              null=True)
    nickname = models.CharField(_(u'nickname'),
                                max_length=100,
                                blank=True)
    slug = models.SlugField(_(u'slug'),
                            max_length=50,
                            unique=True)
    title = models.CharField(_(u'title'),
                             max_length=200,
                             blank=True)
    company = models.ForeignKey(Company,
                                blank=True,
                                null=True)
    about = models.TextField(_(u'about'),
                             blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_(u'user'))
    phone_number = GenericRelation('PhoneNumber')
    date_added = models.DateTimeField(_('date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'contacts_people'
        ordering = ('last_name', 'first_name')
        verbose_name = _(u'person')
        verbose_name_plural = _(u'people')

    def __unicode__(self):
        return self.fullname

    @property
    def fullname(self):
        return u"%s %s" % (self.first_name, self.last_name)


class Group(models.Model):
    """Group model."""
    name = models.CharField(_(u'name'),
                            max_length=200,
                            unique=True)
    slug = models.SlugField(_(u'slug'),
                            max_length=50,
                            unique=True)
    about = models.TextField(_(u'about'),
                             blank=True)
    people = models.ManyToManyField(Person,
                                    verbose_name=_(u'people'),
                                    blank=True,
                                    null=True)
    companies = models.ManyToManyField(Company,
                                       verbose_name=_(u'companies'),
                                       blank=True,
                                       null=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'contacts_groups'
        ordering = ('name',)
        verbose_name = _(u'group')
        verbose_name_plural = _(u'groups')

    def __unicode__(self):
        return u"%s" % self.name


PHONE_LOCATION_CHOICES = (
    ('work', _(u'Work')),
    ('mobile', _(u'Mobile')),
    ('fax', _(u'Fax')),
    ('pager', _(u'Pager')),
    ('home', _(u'Home')),
    ('other', _(u'Other')),
)


class PhoneNumber(models.Model):
    """Phone Number model."""
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={'app_label': 'contacts'})
    object_id = models.IntegerField(db_index=True)
    content_object = generic.GenericForeignKey()
    phone_number = models.CharField(_(u'number'),
                                    max_length=50)
    location = models.CharField(_(u'location'),
                                max_length=6,
                                choices=PHONE_LOCATION_CHOICES,
                                default='work')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.phone_number, self.location)

    class Meta:
        db_table = 'contacts_phone_numbers'
        verbose_name = _(u'phone number')
        verbose_name_plural = _(u'phone numbers')


LOCATION_CHOICES = (
    ('work', _(u'Work')),
    ('home', _(u'Home')),
    ('mobile', _(u'Mobile')),
    ('fax', _(u'Fax')),
    ('person', _(u'Personal')),
    ('other', _(u'Other'))
)


class EmailAddress(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={'app_label': 'contacts'})
    object_id = models.IntegerField(db_index=True)
    content_object = generic.GenericForeignKey()
    email_address = models.EmailField(_(u'email address'))
    location = models.CharField(_(u'location'),
                                max_length=6,
                                choices=LOCATION_CHOICES,
                                default='work')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.email_address, self.location)

    class Meta:
        db_table = 'contacts_email_addresses'
        verbose_name = _(u'email address')
        verbose_name_plural = _(u'email addresses')


IM_SERVICE_CHOICES = (
    ('aim', 'AIM'),
    ('msn', 'MSN'),
    ('icq', 'ICQ'),
    ('jabber', 'Jabber'),
    ('yahoo', 'Yahoo'),
    ('skype', 'Skype'),
    ('qq', 'QQ'),
    ('sametime', 'Sametime'),
    ('gadu-gadu', 'Gadu-Gadu'),
    ('google-talk', 'Google Talk'),
    ('twitter', 'Twitter'),
    ('other', _(u'Other'))
)


class WebSite(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={'app_label': 'contacts'})
    object_id = models.IntegerField(db_index=True)
    content_object = generic.GenericForeignKey()
    url = models.URLField(_(u'URL'))
    location = models.CharField(_(u'location'),
                                max_length=6,
                                choices=LOCATION_CHOICES,
                                default='work')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.url, self.location)

    class Meta:
        db_table = 'contacts_web_sites'
        verbose_name = _(u'web site')
        verbose_name_plural = _(u'web sites')

    def get_absolute_url(self):
        return u"%s?web_site=%s" % (self.content_object.get_absolute_url(), self.pk)


class StreetAddress(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to={'app_label': 'contacts'})
    object_id = models.IntegerField(db_index=True)
    content_object = generic.GenericForeignKey()
    street = models.TextField(_(u'street'),
                              blank=True)
    city = models.CharField(_(u'city'),
                            max_length=200,
                            blank=True)
    province = models.CharField(_(u'province'),
                                max_length=200,
                                blank=True)
    postal_code = models.CharField(_(u'postal code'),
                                   max_length=10,
                                   blank=True)
    country = CountryField(_(u'country'))
    location = models.CharField(_(u'location'),
                                max_length=6,
                                choices=LOCATION_CHOICES,
                                default='work')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.city, self.location)

    class Meta:
        db_table = 'contacts_street_addresses'
        verbose_name = _(u'street address')
        verbose_name_plural = _(u'street addresses')


class CompanyBalanceHistory(models.Model):
    """ Company balance history Model """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"company"))
    amount_debited = models.DecimalField(_(u'amount debited'),
                                         max_digits=12,
                                         decimal_places=4)
    amount_refund = models.DecimalField(_(u'amount refund'),
                                        max_digits=12,
                                        decimal_places=4)
    customer_balance = models.DecimalField(_(u'customer balance'),
                                           max_digits=12,
                                           decimal_places=4,
                                           default=0,
                                           help_text=_(u"""Resulting customer
                                           balance."""))
    supplier_balance = models.DecimalField(_(u'provider balance'),
                                           max_digits=12,
                                           decimal_places=4,
                                           default=0,
                                           help_text=_(u"""Resulting provider
                                           balance."""))
    OPERATION_TYPE_CHOICES = (
        ('customer', _(u"operation on customer account")),
        ('provider', _(u"operation on provider account")),
    )
    operation_type = models.CharField(_(u"operation type"),
                                      max_length=10,
                                      choices=OPERATION_TYPE_CHOICES,
                                      default='customer')
    reference = models.CharField(_(u'public description'),
                                 max_length=255,
                                 blank=True)
    description = models.CharField(_(u'internal description'),
                                   max_length=255,
                                   blank=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'company_balance_history'
        ordering = ('company', 'date_added')
        verbose_name = _(u'Company balance history')
        verbose_name_plural = _(u'Company balance history')

    def __unicode__(self):
        return u"%s %s %s %s" % (self.company,
                                 self.amount_debited,
                                 self.amount_refund,
                                 self.operation_type)


class CustomerDirectory(models.Model):
    """ Customer Directory Model """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"company"))
    registration = models.BooleanField(_(u"Registration"),
                                       default=False,
                                       help_text=_(u"""Is registration needed
                                       for calling ? True, the phone needs to
                                       register with correct username/password.
                                       If false, you must specify a CIDR in SIP
                                       IP CIDR !"""))
    password = models.CharField(_(u"password"),
                                max_length=100,
                                blank=True,
                                help_text=_(u"""It's recommended to use strong
                                passwords for the endpoint."""))
    description = models.TextField(_(u'description'),
                                   blank=True)
    name = models.CharField(_(u"SIP username"),
                            max_length=50,
                            unique=True,
                            help_text=_(u"Ex.: customer SIP username, etc..."))
    rtp_ip = models.CharField(_(u"RTP IP CIDR"),
                              max_length=100,
                              default="auto",
                              help_text=_(u"""Internal IP address/mask to bind
                              to for RTP. Format : CIDR Ex. 192.168.1.0/32"""))
    sip_ip = models.CharField(_(u"SIP IP CIDR"),
                              max_length=100,
                              null=True,
                              blank=True,
                              validators=[validate_cidr],
                              help_text=_(u"""Internal IP address/mask to bind
                              to for SIP. Format : CIDR. Ex. 192.168.1.0/32
                              """))
    sip_port = models.PositiveIntegerField(_(u"SIP port"),
                                           default=5060)
    max_calls = models.PositiveIntegerField(_(u'max calls'),
                                            default=1,
                                            help_text=_(u"""max simultaneous
                                            calls allowed for this customer
                                            account."""))
    calls_per_second = models.PositiveIntegerField(_(u'max calls per second'),
                                                   default=10,
                                                   help_text=_(u"""maximum
                                                   calls per second allowed for
                                                   this customer account."""))
    log_auth_failures = models.BooleanField(_(u"log auth failures"),
                                            default=False,
                                            help_text=_(u"""It true, the server
                                            will log authentication failures.
                                            Required for Fail2ban."""))
    MULTIPLE_CODECS_CHOICES = (
        ("PCMA,PCMU,G729", _(u"PCMA,PCMU,G729")),
        ("PCMU,PCMA,G729", _(u"PCMU,PCMA,G729")),
        ("G729,PCMA,PCMU", _(u"G729,PCMA,PCMU")),
        ("G729,PCMU,PCMA", _(u"G729,PCMU,PCMA")),
        ("PCMA,G729", _(u"PCMA,G729")),
        ("PCMU,G729", _(u"PCMU,G729")),
        ("G729,PCMA", _(u"G729,PCMA")),
        ("G729,PCMU", _(u"G729,PCMU")),
        ("PCMA,PCMU", _(u"PCMA,PCMU")),
        ("PCMU,PCMA", _(u"PCMU,PCMA")),
        ("G722,PCMA,PCMU", _(u"G722,PCMA,PCMU")),
        ("G722,PCMU,PCMA", _(u"G722,PCMU,PCMA")),
        ("G722", _(u"G722")),
        ("G729", _(u"G729")),
        ("PCMU", _(u"PCMU")),
        ("PCMA", _(u"PCMA")),
        ("ALL", _(u"ALL")),
    )
    codecs = models.CharField(_(u"Codecs"),
                              max_length=100,
                              default="ALL",
                              choices=MULTIPLE_CODECS_CHOICES,
                              help_text=_(u"""Codecs allowed - beware about
                              order, 1st has high priority """))
    MULTIPLE_REG_CHOICES = (
        ("call-id", _(u"Call-id")),
        ("contact", _(u"Contact")),
        ("false", _(u"False")),
        ("true", _(u"True")))
    multiple_registrations = models.CharField(_(u"multiple registrations"),
                                              max_length=100,
                                              default="false",
                                              choices=MULTIPLE_REG_CHOICES,
                                              help_text=_(u"""Used to allow to
                                              call one extension and ring
                                              several phones."""))
    outbound_caller_id_name = models.CharField(_(u"CallerID name"),
                                               max_length=50,
                                               blank=True,
                                               help_text=_(u"""Caller ID name
                                               sent to provider on outbound
                                               calls."""))
    outbound_caller_id_number = models.CharField(_(u"""CallerID
                                                   num"""),
                                                 max_length=80,
                                                 blank=True,
                                                 help_text=_(u"""Caller ID
                                                 number sent to provider on
                                                 outbound calls."""))
    IEM_CHOICES = (
        ("false", _(u"false")),
        ("true", _(u"true")),
        ("ring_ready", _(u"ring_ready")))
    ignore_early_media = models.CharField(_(u"Ignore early media"),
                                          max_length=20,
                                          default="false",
                                          choices=IEM_CHOICES,
                                          help_text=_(u"""Controls if the call
                                                      returns on early media
                                                      or not. Default is false.
                                                      Setting the value to
                                                      "ring_ready" will work
                                                      the same as
                                                      ignore_early_media=true
                                                      but also send a SIP 180
                                                      to the inbound leg when
                                                      the first SIP 183 is
                                                      caught.
                                                      """))
    enabled = models.BooleanField(_(u"Enabled / Disabled"),
                                  default=True)
    fake_ring = models.BooleanField(_(u"Fake ring"),
                                    default=False,
                                    help_text=_(u"""Fake ring : Enabled /
                                    Disabled - Send a fake ring to the
                                    caller."""))
    cli_debug = models.BooleanField(_(u"CLI debug"),
                                    default=False,
                                    help_text=_(u"""CLI debug : Enabled /
                                    Disabled - Permit to see all debug
                                    messages on cli."""))
    vmd = models.BooleanField(_(u"Voicemail detection : Enabled / Disabled"),
                              default=False,
                              help_text=_(u"""Be carefull with this option, as
                              it takes a lot of ressources !."""))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'customer_directory'
        ordering = ('company', 'name')
        verbose_name = _(u'Customer sip account')
        verbose_name_plural = _(u'Customer sip accounts')

    def __unicode__(self):
        return "%s (%s:%s)" % (self.name, self.sip_ip, self.sip_port)

    def clean(self):
        if (self.registration and
                (self.password is None or self.password == '')):
            raise ValidationError(_(u"""You have to specify a password if you
                                  want to allow registration"""))
        if (self.registration is False and
                (self.sip_ip is None or self.sip_ip == '')):
            raise ValidationError(_(u"""You must specify a SIP IP CIDR if you do
                                  not want to use registration"""))
        if self.registration and self.password:
            # in future use https://github.com/dstufft/django-passwords ?
            MIN_LENGTH = 8
            if len(self.password) < MIN_LENGTH:
                raise ValidationError(_(u"""The password must be at least %d
                                      characters long.""") % MIN_LENGTH)
            first_isalpha = self.password[0].isalpha()
            if all(c.isalpha() == first_isalpha for c in self.password):
                raise ValidationError(_(u"""The new password must contain
                                            at least one letter and at least
                                            one digit"""))
        if self.sip_ip:
            m = re.search('/32$', self.sip_ip)
            if m:
                pass
            elif len(IPNetwork(self.sip_ip)) == 1:
                self.sip_ip = str(self.sip_ip) + str('/32')
                # add name check no space ...

# Caller ID list


class CalleridPrefixList(models.Model):
    """ CallerID List """
    name = models.CharField(_(u'name'),
                            max_length=128,
                            unique=True)
    description = models.TextField(_(u'description'),
                                   blank=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'callerid_prefix_list'
        ordering = ('name',)
        verbose_name = _(u'CallerID prefix list')
        verbose_name_plural = _(u'CallerID prefix lists')

    def __unicode__(self):
        return u"%s" % self.name

    def prefix(self):
        html = '<span><a href="/extranet/pyfreebill/calleridprefix/?calleridprefixlist__id__exact={0}" class="btn btn-inverse btn-mini">Prefix <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.id))
    prefix.allow_tags = True
    prefix.short_description = _(u'prefix')


class CalleridPrefix(models.Model):
    """ Customer Rates Model """
    calleridprefixlist = models.ForeignKey(
        CalleridPrefixList,
        verbose_name=_(u"callerid prefix list"))
    prefix = models.CharField(_(u'numeric prefix'),
                              max_length=30,
                              db_index=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'caller_id_prefix'
        ordering = ('calleridprefixlist', 'prefix')
        unique_together = ("calleridprefixlist", "prefix")
        verbose_name = _(u'Callerid prefix')
        verbose_name_plural = _(u'Callerid prefix')

    def __unicode__(self):
        return u"%s" % self.prefix

# Provider Rates


class ProviderTariff(models.Model):
    """ Provider tariff """
    name = models.CharField(_(u"name"),
                            max_length=128)
    carrier = models.ForeignKey(Company,
                                verbose_name=_(u"Provider"),
                                limit_choices_to={'supplier_enabled': True})
    currency = models.ForeignKey(
        Currency,
        verbose_name=_(u"Currency"))
    lead_strip = models.CharField(_(u'lead strip'),
                                  blank=True,
                                  default='',
                                  max_length=15)
    tail_strip = models.CharField(_(u'tail strip'),
                                  blank=True,
                                  default='',
                                  max_length=15)
    prefix = models.CharField(_(u'prefix'),
                              blank=True,
                              default='',
                              max_length=15)
    suffix = models.CharField(_(u'suffix'),
                              blank=True,
                              default='',
                              max_length=15)
    description = models.TextField(_(u'description'),
                                   blank=True)
    CALLERID_FILTER_CHOICES = (
        ('1', _(u"No filter")),
        ('2', _(u"Prefix authorized")),
        ('3', _(u"Prefix prohibited")),
    )
    callerid_filter = models.CharField(_(u"CallerID Prefix filter"),
                                       max_length=2,
                                       choices=CALLERID_FILTER_CHOICES,
                                       default='1')
    callerid_list = models.ForeignKey(CalleridPrefixList,
                                      verbose_name=_(u"CallerID prefix List"),
                                      blank=True,
                                      null=True)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    quality = models.IntegerField(_(u'quality'),
                                  blank=True,
                                  default='100',
                                  help_text=_(u"Order by quality."))
    reliability = models.IntegerField(_(u'reliability'),
                                      blank=True,
                                      default='100',
                                      help_text=_(u"Order by reliability."))
    cid = models.CharField(_(u'cid'),
                           blank=True,
                           default='',
                           max_length=25,
                           help_text=_(u"Regex to modify CallerID number."))
    enabled = models.BooleanField(_(u"Enabled / Disabled"),
                                  default=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'provider_tariff'
        ordering = ('enabled',
                    'quality',
                    'reliability')
        verbose_name = _(u'provider ratecard')
        verbose_name_plural = _(u'provider ratecards')

    def __unicode__(self):
        return u"%s" % self.name

    def rates(self):
        html = '<span><a href="/extranet/pyfreebill/providerrates/?provider_tariff__id__exact={0}" class="btn btn-inverse btn-mini">Rates <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.id))
    rates.allow_tags = True
    rates.short_description = _(u'rates')


class ProviderRates(models.Model):
    """ Provider Rates Model """
    destination = models.CharField(_(u'destination'),
                                   blank=True,
                                   default='',
                                   null=True,
                                   max_length=128,
                                   db_index=True)
    digits = models.CharField(_(u'numeric prefix'),
                              max_length=30,
                              db_index=True)
    cost_rate = models.DecimalField(_(u'Cost rate'),
                                    max_digits=11,
                                    decimal_places=5)
    block_min_duration = models.IntegerField(_(u'block min duration'),
                                             default=1)
    init_block = models.DecimalField(_(u'Init block rate'),
                                     max_digits=11,
                                     decimal_places=5,
                                     default=0)
    provider_tariff = models.ForeignKey(ProviderTariff)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    enabled = models.BooleanField(_(u"Enabled / Disabled"), default=True)
    date_added = models.DateTimeField(_(u'date added'), auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'), auto_now=True)

    class Meta:
        db_table = 'provider_rates'
        ordering = ('enabled', 'provider_tariff', 'digits')
        index_together = [
            ["provider_tariff", "digits", "enabled"],
        ]
        unique_together = ("digits", "provider_tariff")
        verbose_name = _(u'provider rate')
        verbose_name_plural = _(u'provider rates')

    def __unicode__(self):
        return u"%s %s %s " % (self.digits,
                               self.cost_rate,
                               self.provider_tariff)

    def set_bar(self, value):
        self.bar = value
    simple_import_methods = ('set_bar',)


# LCR


class LCRGroup(models.Model):
    """ LCR group model """
    name = models.CharField(_(u"name"),
                            max_length=128,
                            unique=True)
    description = models.TextField(_(u'description'),
                                   blank=True)
    LCR_TYPE_CHOICES = (
        ('p', _(u"lower price")),
        ('q', _(u"best quality")),
        ('r', _(u"best reliability")),
        ('l', _(u"load balance")),
    )
    lcrtype = models.CharField(_(u"lcr type"),
                               max_length=10,
                               choices=LCR_TYPE_CHOICES,
                               default='p')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'lcr_group'
        ordering = ('name',)
        verbose_name = _(u'LCR')
        verbose_name_plural = _(u'LCRs')

    def __unicode__(self):
        return u"%s %s " % (self.name, self.lcrtype)


class LCRProviders(models.Model):
    """ LCR group model """
    lcr = models.ForeignKey(LCRGroup,
                            verbose_name=_(u"LCR"))
    provider_tariff = models.ForeignKey(ProviderTariff,
                                        verbose_name=_(u"Provider tariff"))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'lcr_providers'
        verbose_name = _(u'LCR provider')
        verbose_name_plural = _(u'LCR providers')

    def __unicode__(self):
        return u"%s - %s " % (self.lcr, self.provider_tariff)

    def rates(self):
        html = '<span><a href="/extranet/pyfreebill/providerrates/?provider_tariff__id__exact={0}" class="btn btn-inverse btn-mini">Rates <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.provider_tariff))
    rates.allow_tags = True
    rates.short_description = _(u'rates')


# Ratecard


class RateCard(models.Model):
    """ RateCard Model """
    name = models.CharField(_(u'name'),
                            max_length=128,
                            unique=True)
    description = models.TextField(_(u'description'),
                                   blank=True)
    currency = models.ForeignKey(Currency,
                                verbose_name=_(u"Currency"))
    lcrgroup = models.ForeignKey(LCRGroup,
                                 verbose_name=_(u"lcr"))
    CALLERID_FILTER_CHOICES = (
        ('1', _(u"No filter")),
        ('2', _(u"Prefix authorized")),
        ('3', _(u"Prefix prohibited")),
    )
    callerid_filter = models.CharField(_(u"CallerID Prefix filter"),
                                       max_length=2,
                                       choices=CALLERID_FILTER_CHOICES,
                                       default='1')
    callerid_list = models.ForeignKey(CalleridPrefixList,
                                      verbose_name=_(u"CallerID prefix List"),
                                      blank=True,
                                      null=True)
    enabled = models.BooleanField(_(u"Enabled / Disabled"),
                                  default=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'ratecard'
        ordering = ('name', 'enabled')
        verbose_name = _(u'Customer ratecard')
        verbose_name_plural = _(u'Customer ratecards')

    def __unicode__(self):
        return u"%s" % self.name

    def rates(self):
        html = '<span><a href="/extranet/pyfreebill/customerrates/?ratecard__id__exact={0}" class="btn btn-inverse btn-mini">Rates <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.id))
    rates.allow_tags = True
    rates.short_description = _(u'Rates')

    def lcr(self):
        html = '<span><a href="/extranet/pyfreebill/lcrgroup/{0}/" class="btn btn-inverse btn-mini">LCR <i class="icon-plus-sign"></i></a></span>'
        return format_html(html, (self.lcrgroup.pk))
    lcr.allow_tags = True
    lcr.short_description = _(u'lcr')


class CustomerRates(models.Model):
    """ Customer Rates Model """
    ratecard = models.ForeignKey(RateCard,
                                 verbose_name=_(u"ratecard"))
    destination = models.CharField(_(u'destination'),
                                   blank=True,
                                   default='',
                                   null=True,
                                   max_length=128,
                                   db_index=True)
    prefix = models.CharField(_(u'numeric prefix'),
                              max_length=30,
                              db_index=True)
    rate = models.DecimalField(_(u'sell rate'),
                               max_digits=11,
                               decimal_places=5,
                               help_text=_(u"to block the prefix, put -1"))
    block_min_duration = models.IntegerField(_(u'Increment'),
                                             default=1)
    minimal_time = models.IntegerField(_(u'Minimal time'),
                                       default=0)
    init_block = models.DecimalField(_(u'Connection fee'),
                                     max_digits=11,
                                     decimal_places=5,
                                     default=0)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    enabled = models.BooleanField(_(u"Enabled"),
                                  default=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'customer_rates'
        ordering = ('ratecard', 'prefix', 'enabled')
        unique_together = ("ratecard", "prefix")
        verbose_name = _(u'customer rate')
        verbose_name_plural = _(u'customer rates')

    def __unicode__(self):
        return u"%s" % self.ratecard


class CustomerRateCards(models.Model):
    """ Customer rates Cards Model """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"company"))
    ratecard = models.ForeignKey(RateCard,
                                 verbose_name=_(u"ratecard"))
    description = models.TextField(_(u'description'),
                                   blank=True)
    tech_prefix = models.CharField(_(u"technical prefix"),
                                   blank=True,
                                   default='',
                                   null=True,
                                   max_length=7)
    DEFAULT_PRIORITY_CHOICES = (
        (1, _(u'1')),
        (2, _(u'2')),
        (3, _(u'3')),
    )
    priority = models.IntegerField(_(u'priority'),
                                   choices=DEFAULT_PRIORITY_CHOICES,
                                   help_text=_(u"""Priority order, 1 is the
                                               higher priority and 3 the
                                               lower one. Correct values
                                               are : 1, 2 or 3 !."""))
    discount = models.DecimalField(_(u'discount'),
                                   max_digits=3,
                                   decimal_places=2,
                                   default=0,
                                   help_text=_(u"""ratecard discount. For
                                               10% discount, enter 10 !"""))
    allow_negative_margin = models.BooleanField(_(u"""Allow calls with
                                                  negative margin"""),
                                                default=False)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'customer_ratecards'
        ordering = ('company', 'priority', 'ratecard')
        verbose_name = _(u'Customer Ratecard Allocation')
        verbose_name_plural = _(u'Customer ratecard Allocations')

    def __unicode__(self):
        return u"%s - Priority: %s Desc: %s" % (self.ratecard,
                                                self.priority,
                                                self.description)


# NORMALIZATION


class DestinationNumberRules(models.Model):
    """ Destination Number Normalization Rules """
    prefix = models.CharField(_(u'numeric prefix'),
                              max_length=30)
    description = models.TextField(_(u'description'),
                                   blank=True)
    format_num = models.CharField(_(u"Rule format"),
                                  max_length=150,
                                  help_text=_(u"""example for Tunisia :
                                      ^216[%d][%d][%d][%d][%d][%d][%d][%d]
                                      $"""))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'destination_norm_rules'
        ordering = ('prefix',)
        verbose_name = _(u'Destination Number Normalization Rule')
        verbose_name_plural = _(u'Destination Number Normalization Rules')

    def __unicode__(self):
        return u"%s -> %s " % (self.prefix, self.format_num)


class CustomerNormalizationRules(models.Model):
    """ Customer Normalization Rules """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"customer"))
    prefix = models.CharField(_(u'rule title'),
                              max_length=30)
    description = models.TextField(_(u'description'),
                                   blank=True)
    remove_prefix = models.CharField(_(u"remove prefix"),
                                     blank=True,
                                     default='',
                                     max_length=15)
    add_prefix = models.CharField(_(u"add prefix"),
                                  blank=True,
                                  default='',
                                  max_length=15)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'customer_norm_rules'
        ordering = ('company', 'prefix')
        verbose_name = _(u'Customer Normalization Rule')
        verbose_name_plural = _(u'Customer Normalization Rules')

    def __unicode__(self):
        return u"%s -> %s -%s +%s" % (self.company,
                                      self.prefix,
                                      self.remove_prefix,
                                      self.add_prefix)


class CarrierNormalizationRules(models.Model):
    """ Carrier Normalization Rules """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"provider"))
    prefix = models.CharField(_(u'rule title'),
                              max_length=30)
    description = models.TextField(_(u'description'),
                                   blank=True)
    remove_prefix = models.CharField(_(u"remove prefix"),
                                     blank=True,
                                     default='',
                                     max_length=15)
    add_prefix = models.CharField(_(u"add prefix"),
                                  blank=True,
                                  default='',
                                  max_length=15)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'carrier_norm_rules'
        ordering = ('company', 'prefix')
        verbose_name = _(u'Provider Normalization Rule')
        verbose_name_plural = _(u'Provider Normalization Rules')

    def __unicode__(self):
        return u"%s -> %s -%s +%s" % (self.company,
                                      self.prefix,
                                      self.remove_prefix,
                                      self.add_prefix)


class CustomerCIDNormalizationRules(models.Model):
    """ Customer Caller ID Number Normalization Rules """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"customer"))
    prefix = models.CharField(_(u'rule title'),
                              max_length=30)
    description = models.TextField(_(u'description'),
                                   blank=True)
    remove_prefix = models.CharField(_(u"remove prefix"),
                                     blank=True,
                                     default='',
                                     max_length=15)
    add_prefix = models.CharField(_(u"add prefix"),
                                  blank=True,
                                  default='',
                                  max_length=15)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'customer_cid_norm_rules'
        ordering = ('company', )
        verbose_name = _(u'Customer CallerID Normalization Rule')
        verbose_name_plural = _(u'Customer CallerID Normalization Rules')

    def __unicode__(self):
        return u"%s -> -%s +%s" % (self.company,
                                   self.remove_prefix,
                                   self.add_prefix)


class CarrierCIDNormalizationRules(models.Model):
    """ Carrier Caller ID Number Normalization Rules """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"provider"))
    prefix = models.CharField(_(u'rule title'),
                              max_length=30)
    description = models.TextField(_(u'description'),
                                   blank=True)
    remove_prefix = models.CharField(_(u"remove prefix"),
                                     blank=True,
                                     default='',
                                     max_length=15)
    add_prefix = models.CharField(_(u"add prefix"),
                                  blank=True,
                                  default='',
                                  max_length=15)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'carrier_cid_norm_rules'
        ordering = ('company', )
        verbose_name = _(u'Provider CallerID Normalization Rule')
        verbose_name_plural = _(u'Provider CallerID Normalization Rules')

    def __unicode__(self):
        return u"%s -> -%s +%s" % (self.company,
                                   self.remove_prefix,
                                   self.add_prefix)

# ACL


class AclLists(models.Model):
    """ ACL list model """
    acl_name = models.CharField(_(u'name'),
                                max_length=128)
    DEFAULT_POLICY_CHOICES = (
        ('deny', _(u'deny')),
        ('allow', _(u'allow')),
    )
    default_policy = models.CharField(_(u'default policy'),
                                      max_length=10,
                                      choices=DEFAULT_POLICY_CHOICES,
                                      default='deny')
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'acl_lists'
        ordering = ('acl_name',)
        verbose_name = _(u'ACL list')
        verbose_name_plural = _(u'ACL lists')

    def __unicode__(self):
        return u"%s" % self.acl_name


class AclNodes(models.Model):
    """ ACL NODES model """
    company = models.ForeignKey(Company,
                                verbose_name=_(u"company"))
    cidr = models.CharField(_(u"ip/cidr Address"),
                            max_length=100,
                            help_text=_(u"Customer IP or cidr address."))
    POLICY_CHOICES = (
        ('deny', _('deny')),
        ('allow', _('allow')),
    )
    policy = models.CharField(_(u"policy"),
                              max_length=10,
                              choices=POLICY_CHOICES,
                              default='allow')
    acllist = models.ForeignKey(AclLists,
                                verbose_name=_(u"acl list"))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'acl_nodes'
        ordering = ('company', 'policy', 'cidr')
        verbose_name = _(u'ACL node')
        verbose_name_plural = _(u'ACL nodes')

    def __unicode__(self):
        return u"%s %s" % (self.company, self.cidr)

# VOIP SWITCH


class VoipSwitch(models.Model):
    """ VoipSwitch Profile """
    name = models.CharField(_(u"Switch name"),
                            max_length=50,
                            help_text=_(u"Switch name"))
    ip = models.CharField(_(u"switch IP"),
                          max_length=100,
                          default="auto",
                          help_text=_(u"Switch IP."))
    esl_listen_ip = models.CharField(_(u"event socket switch IP"),
                                     max_length=100,
                                     default="127.0.0.1",
                                     help_text=_(u"Event socket switch IP."))
    esl_listen_port = models.PositiveIntegerField(_(u"""event socket switch
                                                    port"""),
                                                  default="8021",
                                                  help_text=_(u"""Event socket
                                                              switch port."""))
    esl_password = models.CharField(_(u"event socket switch password"),
                                    max_length=30,
                                    default="ClueCon",
                                    help_text=_(u"""Event socket switch
                                                password."""))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'voip_switch'
        ordering = ('name', )
        verbose_name = _(u'VoIP Switch')
        verbose_name_plural = _(u'VoIP Switches')

    def __unicode__(self):
        return u"%s (:%s)" % (self.name, self.ip)

# SOFIA


class SipProfile(models.Model):
    """ Sofia Sip profile """
    name = models.CharField(_(u"SIP profile name"),
                            max_length=50,
                            unique=True,
                            help_text=_(u"""E.g.: the name you want ..."""))
    user_agent = models.CharField(_(u"User agent name"),
                                  max_length=50,
                                  default="pyfreebilling",
                                  help_text=_(u"""E.g.: the user agent
                                              you want ... - take care
                                              with certain characters
                                              such as @ could cause others sip
                                              proxies reject yours messages as
                                              invalid ! """))
    ext_rtp_ip = models.CharField(_(u"external RTP IP"),
                                  max_length=100,
                                  default="auto",
                                  help_text=_(u"""External/public IP
                                    address to bind to for RTP."""))
    ext_sip_ip = models.CharField(_(u"external SIP IP"),
                                  max_length=100,
                                  default="auto",
                                  help_text=_(u"""External/public IP
                                              address to bind to for
                                              SIP."""))
    rtp_ip = models.CharField(_(u"RTP IP"),
                              max_length=100,
                              default="auto",
                              help_text=_(u"""Internal IP address to bind
                                          to for RTP."""))
    sip_ip = models.CharField(_(u"SIP IP"),
                              max_length=100,
                              default="auto",
                              help_text=_(u"""Internal IP address to bind
                                          to for SIP."""))
    sip_port = models.PositiveIntegerField(_(u"SIP port"),
                                           default=5060)
    disable_transcoding = models.BooleanField(_(u"disable transcoding"),
                                              default=True,
                                              help_text=_(u"""If true, you
                                                          can not use
                                                          transcoding."""))
    accept_blind_reg = models.BooleanField(_(u"accept blind registration"),
                                           default=False,
                                           help_text=_(u"""If true, anyone can
                                                       register to the server
                                                       and will not be
                                                       challenged for
                                                       username/password
                                                       information."""))
    disable_register = models.BooleanField(_(u"disable register"),
                                           default=True,
                                           help_text=_(u"""disable register
                                                       which may be undesirable
                                                       in a public switch """))
    apply_inbound_acl = models.BooleanField(_(u"Apply an inbound ACL"),
                                            default=True,
                                            help_text=_(u"""If true, FS will
                                                      apply the default acl
                                                      list : domains """))
    auth_calls = models.BooleanField(_(u"authenticate calls"),
                                     default=True,
                                     help_text=_(u"""If true, FreeeSWITCH will
                                                 authorize all calls on this
                                                 profile, i.e. challenge the
                                                 other side for
                                                 username/password information.
                                                 """))
    log_auth_failures = models.BooleanField(_(u"log auth failures"),
                                            default=False,
                                            help_text=_(u"""It true, log
                                                      authentication failures.
                                                      Required for Fail2ban.
                                                      """))
    MULTIPLE_CODECS_CHOICES = (
        ("PCMA,PCMU,G729", _(u"PCMA,PCMU,G729")),
        ("PCMU,PCMA,G729", _(u"PCMU,PCMA,G729")),
        ("G729,PCMA,PCMU", _(u"G729,PCMA,PCMU")),
        ("G729,PCMU,PCMA", _(u"G729,PCMU,PCMA")),
        ("PCMA,G729", _(u"PCMA,G729")),
        ("PCMU,G729", _(u"PCMU,G729")),
        ("G729,PCMA", _(u"G729,PCMA")),
        ("G729,PCMU", _(u"G729,PCMU")),
        ("PCMA,PCMU", _(u"PCMA,PCMU")),
        ("PCMU,PCMA", _(u"PCMU,PCMA")),
        ("G722,PCMA,PCMU", _(u"G722,PCMA,PCMU")),
        ("G722,PCMU,PCMA", _(u"G722,PCMU,PCMA")),
        ("G722", _(u"G722")),
        ("G729", _(u"G729")),
        ("PCMU", _(u"PCMU")),
        ("PCMA", _(u"PCMA")),
        ("ALL", _(u"ALL")),
    )
    inbound_codec_prefs = models.CharField(_(u"inbound codec prefs"),
                                           max_length=100,
                                           choices=MULTIPLE_CODECS_CHOICES,
                                           default="G729,PCMU,PCMA",
                                           help_text=_(u"""Define allowed
                                                       preferred codecs for
                                                       inbound calls."""))
    outbound_codec_prefs = models.CharField(_(u"outbound codec prefs"),
                                            max_length=100,
                                            choices=MULTIPLE_CODECS_CHOICES,
                                            default="G729,PCMU,PCMA",
                                            help_text=_(u"""Define allowed
                                                        preferred codecs for
                                                        outbound calls."""))
    aggressive_nat_detection = models.BooleanField(_(u"""Agressive NAT
                                                     detection"""),
                                                   default=False,
                                                   help_text=_(u"""This will
                                                               enable NAT mode
                                                               if the network
                                                               IP/port from
                                                               which therequest
                                                               was received
                                                               differs from the
                                                               IP/Port
                                                               combination in
                                                               the SIP Via:
                                                               header, or if
                                                               the Via: header
                                                               contains the
                                                               received
                                                               parameter"""))
    NDLB_rec_in_nat_reg_c = models.BooleanField(_(u"""NDLB received
                                                  in nat reg contact"""),
                                                default=False,
                                                help_text=_(u"""add a;received=
                                                            "ip:port"
                                                            to the contact when
                                                            replying to
                                                            register
                                                            for nat handling
                                                            """))
    NDLB_FP_CHOICES = (
        ("true", _(u"true")),
        ("safe", _(u"safe")),
    )
    NDLB_force_rport = models.CharField(_(u"""NDLB Force rport"""),
                                        max_length=10,
                                        choices=NDLB_FP_CHOICES,
                                        null=True,
                                        blank=True,
                                        default="Null",
                                        help_text=_(u"""This will force
                                                    FreeSWITCH to send
                                                    SIP responses to the
                                                    network port from
                                                    which they were received.
                                                    Use at your own risk!"""))
    NDLB_broken_auth_hash = models.BooleanField(_(u"""NDLB broken auth hash
                                                  """),
                                                default=False,
                                                help_text=_(u"""Used for when
                                                            phones respond to a
                                                            challenged ACK
                                                            with method INVITE
                                                            in the hash"""))
    enable_timer = models.BooleanField(_(u"""Enable timer"""),
                                       default=False,
                                       help_text=_(u"""This enables or disables
                                                   support for RFC 4028 SIP
                                                   Session Timers"""))
    session_timeout = models.PositiveIntegerField(_(u"""Session timeout"""),
                                                  default=1800,
                                                  help_text=_(u"""session
                                                              timers for all
                                                              call to expire
                                                              after the
                                                              specified seconds
                                                              Then it will send
                                                              another invite
                                                              --re-invite. If
                                                              not specified
                                                              defaults to 30
                                                              minutes. Some
                                                              gateways may
                                                              reject values
                                                              less than 30
                                                              minutes. This
                                                              values refers to
                                                              Session-Expires
                                                              in RFC 4028 -The
                                                              time at which
                                                              an element will
                                                              consider the
                                                              session timed
                                                              out, if no
                                                              successful
                                                              session refresh
                                                              transaction
                                                              occurs
                                                              beforehand-
                                                              """))
    rtp_rewrite_timestamps = models.BooleanField(_(u"""RTP rewrite timestamps"""),
                                       default=False,
                                       help_text=_(u"""If you don't want to pass
                                           through timestampes from 1 RTP call
                                           to another"""))
    pass_rfc2833 = models.BooleanField(_(u"""pass rfc2833"""),
                                       default=False,
                                       help_text=_(u"""pass rfc2833"""))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'sip_profile'
        ordering = ('name', )
        unique_together = ("sip_ip", "sip_port")
        verbose_name = _(u'SIP profile')
        verbose_name_plural = _(u'SIP profiles')

    def __unicode__(self):
        return u"%s (%s:%s)" % (self.name, self.sip_ip, self.sip_port)

    def get_gateways(self):
        """Get all gateways in the system assigned to this sip profile."""
        retval = []
        accounts = Company.objects.filter(supplier_enabled=True)
        for account in accounts:
            for gateway in account.sofiagateway_set.all():
                if gateway.sip_profile.id == self.id:
                    retval.append(gateway)
        return retval


class SofiaGateway(models.Model):
    name = models.CharField(_(u"name"),
                            max_length=100,
                            unique=True)
    sip_profile = models.ForeignKey('SipProfile',
                                    verbose_name=_(u"SIP profile"),
                                    help_text=_(u"""Which Sip Profile
                                        communication with this gateway will
                                        take place on."""))
    company = models.ForeignKey(Company,
                                verbose_name=_(u"Provider"),
                                db_index=True)
    channels = models.PositiveIntegerField(_(u"channels number"),
                                           default=1,
                                           help_text=_(u"""maximum simultaneous
                                               calls allowed for this gateway.
                                               """))
    enabled = models.BooleanField(_(u"Enabled"),
                                  default=True)
    prefix = models.CharField(_(u'prefix'),
                              blank=True,
                              default='',
                              max_length=15)
    suffix = models.CharField(_(u'suffix'),
                              blank=True,
                              default='',
                              max_length=15)
    MULTIPLE_CODECS_CHOICES = (
        ("PCMA,PCMU,G729", _(u"PCMA,PCMU,G729")),
        ("PCMU,PCMA,G729", _(u"PCMU,PCMA,G729")),
        ("G729,PCMA,PCMU", _(u"G729,PCMA,PCMU")),
        ("G729,PCMU,PCMA", _(u"G729,PCMU,PCMA")),
        ("PCMA,G729", _(u"PCMA,G729")),
        ("PCMU,G729", _(u"PCMU,G729")),
        ("G729,PCMA", _(u"G729,PCMA")),
        ("G729,PCMU", _(u"G729,PCMU")),
        ("PCMA,PCMU", _(u"PCMA,PCMU")),
        ("PCMU,PCMA", _(u"PCMU,PCMA")),
        ("G722,PCMA,PCMU", _(u"G722,PCMA,PCMU")),
        ("G722,PCMU,PCMA", _(u"G722,PCMU,PCMA")),
        ("G722", _(u"G722")),
        ("G729", _(u"G729")),
        ("PCMU", _(u"PCMU")),
        ("PCMA", _(u"PCMA")),
        ("ALL", _(u"ALL")),
    )
    codec = models.CharField(_(u"Codecs"),
                              max_length=30,
                              default="ALL",
                              choices=MULTIPLE_CODECS_CHOICES,
                              help_text=_(u"""Codecs allowed - beware about
                              order, 1st has high priority """))
    username = models.CharField(_(u"username"),
                                blank=True,
                                default='',
                                max_length=35)
    password = models.CharField(_(u"password"),
                                blank=True,
                                default='',
                                max_length=35)
    register = models.BooleanField(_(u"register"),
                                   default=False)
    proxy = models.CharField(_(u"proxy"),
                             max_length=48,
                             default="",
                             help_text=_(u"IP if register is False."))
    extension = models.CharField(_(u"extension number"),
                                 max_length=50,
                                 blank=True,
                                 default="",
                                 help_text=_(u"""Extension for inbound calls.
                                     Same as username, if blank."""))
    realm = models.CharField(_(u"realm"),
                             max_length=50,
                             blank=True,
                             default="",
                             help_text=_(u"""Authentication realm. Same as
                                 gateway name, if blank."""))
    from_domain = models.CharField(_(u"from domain"),
                                   max_length=50,
                                   blank=True,
                                   default="",
                                   help_text=_(u"""Domain to use in from field.
                                       Same as realm if blank."""))
    expire_seconds = models.PositiveIntegerField(_(u"expire seconds"),
                                                 default=3600,
                                                 null=True)
    retry_seconds = models.PositiveIntegerField(_(u"retry seconds"),
                                                default=30,
                                                null=True,
                                                help_text=_(u"""How many
                                                    seconds before a retry when
                                                    a failure or timeout occurs
                                                    """))
    caller_id_in_from = models.BooleanField(_(u"caller ID in From field"),
                                            default=True,
                                            help_text=_(u"""Use the callerid of
                                                an inbound call in the from
                                                field on outbound calls via
                                                this gateway."""))
    SIP_CID_TYPE_CHOICES = (
        ('none', _(u'none')),
        ('default', _(u'default')),
        ('pid', _(u'pid')),
        ('rpid', _(u'rpid')),
    )
    sip_cid_type = models.CharField(_(u'SIP CID type'),
                                    max_length=10,
                                    choices=SIP_CID_TYPE_CHOICES,
                                    default='rpid',
                                    help_text=_(u"""Modify callerID in SDP
                                        Headers."""))
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'sofia_gateway'
        ordering = ('company', 'name')
        verbose_name = _(u"Sofia gateway")
        verbose_name_plural = _(u"Sofia gateways")

    def __unicode__(self):
        return u"%s" % self.name

# Hangup Cause


class HangupCause(models.Model):
    """ Hangup Cause Model """
    code = models.PositiveIntegerField(_(u"Hangup code"),
                                       unique=True,
                                       help_text=_(u"ITU-T Q.850 Code."))
    enumeration = models.CharField(_(u"enumeration"),
                                   max_length=100,
                                   null=True,
                                   blank=True,
                                   help_text=_(u"enumeration."))
    cause = models.CharField(_(u"cause"),
                             max_length=100,
                             null=True,
                             blank=True,
                             help_text=_(u"Cause."))
    description = models.TextField(_(u'description'),
                                   blank=True)
    date_added = models.DateTimeField(_(u'date added'),
                                      auto_now_add=True)
    date_modified = models.DateTimeField(_(u'date modified'),
                                         auto_now=True)

    class Meta:
        db_table = 'hangup_cause'
        ordering = ('code',)
        verbose_name = _(u"hangupcause")
        verbose_name_plural = _(u"hangupcauses")

    def __unicode__(self):
        return u"[%s] %s" % (self.code, self.enumeration)

# CDR


class CDR(models.Model):
    """ CDR Model    """
    customer = models.ForeignKey(Company, verbose_name=_(u"customer"), null=True, related_name="customer_related")
    customer_ip = models.CharField(_(u"customer IP address"), max_length=100, null=True, help_text=_(u"Customer IP address."))
    uuid = models.CharField(_(u"UUID"), max_length=100, null=True)
    bleg_uuid = models.CharField(_(u"b leg UUID"), null=True, default="", max_length=100)
    caller_id_number = models.CharField(_(u"caller ID num"), max_length=100, null=True)
    destination_number = models.CharField(_(u"Dest. number"), max_length=100, null=True)
    chan_name = models.CharField(_(u"channel name"), max_length=100, null=True)
    start_stamp = models.DateTimeField(_(u"start time"), null=True, db_index=True)
    answered_stamp = models.DateTimeField(_(u"answered time"), null=True)
    end_stamp = models.DateTimeField(_(u"hangup time"), null=True)
    duration = models.IntegerField(_(u"global duration"), null=True)
    effectiv_duration = models.IntegerField(_(u"total duration"), null=True, help_text=_(u"Global call duration since call has been received by the switch in ms."))
    effective_duration = models.IntegerField(_(u"effective duration"), null=True, help_text=_(u"real call duration in s."))
    billsec = models.IntegerField(_(u"billed duration"), null=True, help_text=_(u"billed call duration in s."))
    read_codec = models.CharField(_(u"read codec"), max_length=20, null=True)
    write_codec = models.CharField(_(u"write codec"), max_length=20, null=True)
    hangup_cause = models.CharField(_(u"hangup cause"), max_length=50, null=True, db_index=True)
    hangup_cause_q850 = models.IntegerField(_(u"q.850"), null=True)
    gateway = models.ForeignKey(SofiaGateway, verbose_name=_(u"gateway"), null=True)
    cost_rate = models.DecimalField(_(u'buy rate'), max_digits=11, decimal_places=5, default="0", null=True)
    total_sell = models.DecimalField(_(u'total sell'), max_digits=11, decimal_places=5, default="0", null=True)
    total_cost = models.DecimalField(_(u'total cost'), max_digits=11, decimal_places=5, default="0", null=True)
    prefix = models.CharField(_(u'Prefix'), max_length=30, null=True)
    country = models.CharField(_(u'Country'), max_length=100, null=True)
    rate = models.DecimalField(_(u'sell rate'), max_digits=11, decimal_places=5, null=True)
    init_block = models.DecimalField(_(u'Connection fee'), max_digits=11, decimal_places=5, null=True)
    block_min_duration = models.IntegerField(_(u'increment'), null=True)
    lcr_carrier_id = models.ForeignKey(Company, verbose_name=_(u"provider"), null=True, related_name="carrier_related")
    ratecard_id = models.ForeignKey(RateCard, null=True, verbose_name=_(u"ratecard"))
    lcr_group_id = models.ForeignKey(LCRGroup, null=True, verbose_name=_(u"lcr group"))
    sip_user_agent = models.CharField(_(u'sip user agent'), null=True, max_length=100)
    sip_rtp_rxstat = models.CharField(_(u'sip rtp rx stat'), null=True, max_length=30)
    sip_rtp_txstat = models.CharField(_(u'sip rtp tx stat'), null=True, max_length=30)
    switchname = models.CharField(_(u"switchname"), null=True, default="", max_length=100)
    switch_ipv4 = models.CharField(_(u"switch ipv4"), null=True, default="", max_length=100)
    hangup_disposition = models.CharField(_(u"hangup disposition"), null=True, default="", max_length=100)
    sip_hangup_cause = models.CharField(_(u"SIP hangup cause"), null=True, default="", max_length=100)
    sell_destination = models.CharField(_(u'sell destination'), blank=True, default='', null=True, max_length=128, db_index=True)
    cost_destination = models.CharField(_(u'cost destination'), blank=True, default='', null=True, max_length=128, db_index=True)

    class Meta:
        db_table = 'cdr'
        ordering = ('start_stamp', 'customer')
        verbose_name = _(u"CDR")
        verbose_name_plural = _(u"CDRs")

    def __unicode__(self):
        if self.start_stamp:
            return self.start_stamp
        else:
            return self.custom_alias_name

    def hangup_cause_colored(self):
        if self.billsec == 0:
            color = "red"
        else:
            color = "green"
        return " <span style=color:%s>%s</span>" % (color, self.hangup_cause)
    hangup_cause_colored.allow_tags = True

    @property
    def daily_total_answered_calls(self):
        return qsstats.QuerySetStats(self.objects.all().exclude(effective_duration="0").filter(hangup_cause="NORMAL_CLEARING"), 'start_stamp', aggregate=Count('id')).this_day()

    @property
    def daily_total_calls(self):
        return qsstats.QuerySetStats(self.objects.all(), 'start_stamp', aggregate=Count('id')).this_day()

    @property
    def daily_total_effective_duration_calls(self):
        return qsstats.QuerySetStats(self.objects.all().exclude(effective_duration="0").filter(hangup_cause="NORMAL_CLEARING"), 'start_stamp', aggregate=Sum('effective_duration')).this_day()

    @property
    def daily_total_sell_calls(self):
        return qsstats.QuerySetStats(self.objects.all().exclude(effective_duration="0").filter(hangup_cause="NORMAL_CLEARING"), 'start_stamp', aggregate=Sum('total_sell')).this_day()

    @property
    def daily_total_cost_calls(self):
        return qsstats.QuerySetStats(self.objects.all().exclude(effective_duration="0").filter(hangup_cause="NORMAL_CLEARING"), 'start_stamp', aggregate=Sum('total_cost')).this_day()

    def _get_min_effective_duration(self):
        if self.effective_duration:
            min = int(self.effective_duration / 60)
            sec = int(self.effective_duration % 60)
        else:
            min = 0
            sec = 0

        return "%02d:%02d" % (min, sec)
    min_effective_duration = property(_get_min_effective_duration)

    def _get_total_sell(self):
        if self.rate and self.rate != 0:
            totalsell = decimal.Decimal(self.billsec) * decimal.Decimal(self.rate) / 60
        else:
            totalsell = 0.000000
        if self.init_block:
            totalsell = decimal.Decimal(totalsell) + decimal.Decimal(self.init_block)
        return round(totalsell, 6)
    total_sell_py = property(_get_total_sell)

    def _get_total_cost(self):
        if self.cost_rate:
            totalcost = decimal.Decimal(self.effective_duration) * decimal.Decimal(self.cost_rate) / 60
        else:
            totalcost = 0.000000
        return round(totalcost, 6)
    total_cost_py = property(_get_total_cost)

    def _get_effective_duration(self):
        if self.effectiv_duration:
            effdur = math.ceil(self.effectiv_duration / 1000.0)
        else:
            effdur = 0
        return int(effdur)
    effective_duration_py = property(_get_effective_duration)

    def _get_billsec(self):
        if self.block_min_duration and self.effective_duration:
            if self.effective_duration < self.block_min_duration:
                billsec = self.block_min_duration
            else:
                billsec = math.ceil(self.effective_duration / self.block_min_duration) * self.block_min_duration
        else:
            billsec = self.effective_duration
        return int(billsec)
    billsec_py = property(_get_billsec)

    def success_cdr(self):
        return self.CDR.objects.exclude(effective_duration="0")

# STATS


class DimDate(models.Model):
    """ Date dimension """
    date = models.DateTimeField()
    day = models.CharField(_(u'day'), max_length=2)
    day_of_week = models.CharField(_(u'day of the week'), max_length=30)
    hour = models.CharField(_(u'hour'), max_length=2, null=True, blank=True)
    month = models.CharField(_(u'month'), max_length=2)
    quarter = models.CharField(_(u'quarter'), max_length=2)
    year = models.CharField(_(u'year'), max_length=4)

    class Meta:
        db_table = 'date_dimension'
        ordering = ('date',)
        verbose_name = _(u"date dimension")
        verbose_name_plural = _(u"date dimensions")

    def __unicode__(self):
        return u"%s" % self.date


class DimCustomerHangupcause(models.Model):
    """ Dimension Customer / Hangupcause Model """
    customer = models.ForeignKey(Company, verbose_name=_(u"customer"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    hangupcause = models.CharField(_(u'hangupcause'), max_length=100, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"))

    class Meta:
        db_table = 'dim_customer_hangupcause'
        ordering = ('date', 'customer', 'hangupcause')
        verbose_name = _(u"Customer Hangupcause stats")
        verbose_name_plural = _(u"Customer Hangupcause stats")

    def __unicode__(self):
        return u"%s -c: %s -h: %s" % (self.date, self.customer, self.hangupcause)


class DimCustomerSipHangupcause(models.Model):
    """ Dimension Customer / SIP Hangupcause Model """
    customer = models.ForeignKey(Company, verbose_name=_(u"customer"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    sip_hangupcause = models.CharField(_(u'sip hangupcause'), max_length=100, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"))

    class Meta:
        db_table = 'dim_customer_sip_hangupcause'
        ordering = ('date', 'customer', 'sip_hangupcause')
        verbose_name = _(u"Customer SIP Hangupcause stats")
        verbose_name_plural = _(u"Customer SIP Hangupcause stats")

    def __unicode__(self):
        return u"%s -c: %s -h: %s" % (self.date, self.customer, self.sip_hangupcause)


class DimProviderHangupcause(models.Model):
    """ Dimension Provider / Hangupcause Model """
    provider = models.ForeignKey(Company, verbose_name=_(u"provider"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    hangupcause = models.CharField(_(u'hangupcause'), max_length=100, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"))

    class Meta:
        db_table = 'dim_provider_hangupcause'
        ordering = ('date', 'provider', 'hangupcause')
        verbose_name = _(u"Provider Hangupcause stats")
        verbose_name_plural = _(u"Provider Hangupcause stats")

    def __unicode__(self):
        return u"%s -c: %s -h: %s" % (self.date, self.provider, self.hangupcause)


class DimProviderSipHangupcause(models.Model):
    """ Dimension Provider / SIP Hangupcause Model """
    provider = models.ForeignKey(Company, verbose_name=_(u"provider"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    sip_hangupcause = models.CharField(_(u'sip hangupcause'), max_length=100, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"))

    class Meta:
        db_table = 'dim_provider_sip_hangupcause'
        ordering = ('date', 'provider', 'sip_hangupcause')
        verbose_name = _(u"Provider SIP Hangupcause stats")
        verbose_name_plural = _(u"Provider SIP Hangupcause stats")

    def __unicode__(self):
        return u"%s -c: %s -h: %s" % (self.date, self.provider, self.sip_hangupcause)


class DimCustomerDestination(models.Model):
    """ Dimension Customer / Destination Model """
    customer = models.ForeignKey(Company, verbose_name=_(u"customer"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"), default=0)
    success_calls = models.IntegerField(_(u"success calls"), default=0)
    total_duration = models.IntegerField(_(u"total duration"), default=0)
    avg_duration = models.IntegerField(_(u"average duration"), default=0)
    max_duration = models.IntegerField(_(u"max duration"), default=0)
    min_duration = models.IntegerField(_(u"min duration"), default=0)
    total_sell = models.DecimalField(_(u'total sell'), max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(_(u'total cost'), max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'dim_customer_destination'
        ordering = ('date', 'customer', 'destination')
        verbose_name = _(u"Customer destination stats")
        verbose_name_plural = _(u"Customer destination stats")

    def __unicode__(self):
        return u"%s -c: %s -d: %s" % (self.date, self.customer, self.destination)

    def _get_margin(self):
        if self.total_sell and self.total_cost:
            margin = self.total_sell - self.total_cost
        else:
            margin = 0
        return round(margin, 2)
    margin = property(_get_margin)


class DimProviderDestination(models.Model):
    """ Dimension Provider / Destination Model """
    provider = models.ForeignKey(Company, verbose_name=_(u"provider"))
    destination = models.CharField(_(u'destination'), max_length=250, null=True, blank=True)
    date = models.ForeignKey(DimDate, verbose_name=_(u"date"))
    total_calls = models.IntegerField(_(u"total calls"), default=0)
    success_calls = models.IntegerField(_(u"success calls"), default=0)
    total_duration = models.IntegerField(_(u"total duration"), default=0)
    avg_duration = models.IntegerField(_(u"average duration"), default=0)
    max_duration = models.IntegerField(_(u"max duration"), default=0)
    min_duration = models.IntegerField(_(u"min duration"), default=0)
    total_sell = models.DecimalField(_(u'total sell'), max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(_(u'total cost'), max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'dim_provider_destination'
        ordering = ('date', 'provider', 'destination')
        verbose_name = _(u"Provider destination stats")
        verbose_name_plural = _(u"Provider destination stats")

    def __unicode__(self):
        return u"%s -p: %s -d: %s" % (self.date, self.provider, self.destination)

    def get_daily_providers_stats(self, today, delta, interval):
        qs = self.model._default_manager.filter(date__lte=lastday)
        qss = qsstats.QuerySetStats(qs, 'date')
        lastday = today - datetime.timedelta(days=delta)
        return qss.time_series(lastday, today, interval)

    def get_current_week_daily_provider_stats(self, period, interval):
        today = datetime.date.today()
        return self.get_daily_providers_stats(today, period, interval)

    def get_day_total_calls(self):
        qs = DimProviderDestination.objects.all()
        day_qs = qs.values('date').annotate(day_total_calls=Sum('total_calls'), day_success_calls=Sum('success_calls'), day_total_duration=Sum('total_duration'), day_total_sell=Sum('total_sell'), day_total_cost=Sum('total_cost')).order_by('date')
        return [t[1] for t in day_qs]
