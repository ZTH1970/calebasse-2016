# -*- coding: utf-8 -*-

from datetime import datetime, date, time as datetime_time

from django.db import models
from django.db.models import query
from django.contrib.auth.models import User
from django.template.defaultfilters import date as date_filter
from django import forms

import reversion

from calebasse.models import PhoneNumberField
from calebasse.ressources.models import Service, NamedAbstractModel
from calebasse.models import BaseModelMixin, WeekRankField
from calebasse.utils import weeks_since_epoch, weekday_ranks

from interval import Interval

from model_utils import Choices
from model_utils.managers import PassThroughManager

class Role(NamedAbstractModel):
    users = models.ManyToManyField(User,
                verbose_name=u'Utilisateurs', blank=True)

class People(BaseModelMixin, models.Model):
    GENDERS =  Choices(
            (1, 'Masculin'),
            (2, 'Féminin'),
    )

    last_name = models.CharField(max_length=128, verbose_name=u'Nom')
    first_name = models.CharField(max_length=128, verbose_name=u'Prénom(s)')
    display_name = models.CharField(max_length=256,
            verbose_name=u'Nom complet', editable=False)
    gender = models.IntegerField(verbose_name=u"Genre", choices=GENDERS,
            max_length=1, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(verbose_name=u"Téléphone", blank=True, null=True)

    def save(self, **kwargs):
        self.display_name = self.first_name + ' ' + self.last_name.upper()
        super(People, self).save(**kwargs)

    def __unicode__(self):
        return self.display_name

    def get_initials(self):
        initials = []
        if self.first_name:
            initials.append(self.first_name[0].upper())
        initials.append(self.last_name[0].upper())
        return ''.join(initials)

    class Meta:
        ordering = ['last_name', 'first_name']

class WorkerQuerySet(query.QuerySet):
    def for_service(self, service, type=None):
        if type:
            return self.filter(enabled=True, services__in=[service], type=type)
        else:
            return self.filter(enabled=True, services__in=[service])


class Worker(People):
    objects = PassThroughManager.for_queryset_class(WorkerQuerySet)()
    type = models.ForeignKey('ressources.WorkerType',
            verbose_name=u'Type de personnel')
    services = models.ManyToManyField('ressources.Service')
    enabled = models.BooleanField(verbose_name=u'Actif',
                default=True)
    old_camsp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CAMSP', blank=True, null=True)
    old_cmpp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CMPP', blank=True, null=True)
    old_sessad_dys_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD TED', blank=True, null=True)
    old_sessad_ted_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD DYS', blank=True, null=True)

    def is_active(self):
        return self.enabled

    def is_away(self):
        if self.timetable_set.filter(weekday=date.today().weekday()).exists():
            return False
        return True

    @models.permalink
    def get_absolute_url(self):
        return ('worker_update', (), {
            'service': self.services.all()[0].name.lower(),
            'pk': self.pk })

    class Meta:
        verbose_name = u'Personnel'
        verbose_name_plural = u'Personnels'

reversion.register(Worker, follow=['people_ptr'])
reversion.register(User)

class UserWorker(BaseModelMixin, models.Model):
    user = models.OneToOneField('auth.User')
    worker = models.ForeignKey('Worker',
            verbose_name=u'Personnel')

    def __unicode__(self):
        return u'Lien entre la personne {0} et l\'utilisateur {1}'.format(
                self.worker, self.user)

reversion.register(UserWorker)

class SchoolTeacher(People):
    schools = models.ManyToManyField('ressources.School')
    role = models.ForeignKey('ressources.SchoolTeacherRole')

reversion.register(SchoolTeacher, follow=['user_ptr'])

class TimeTableQuerySet(query.QuerySet):
    def current(self, today=None):
        if today is None:
            today = date.today()
        return self.filter(start_date__lte=today, end_date__gte=today)

    def for_today(self, today=None):
        if today is None:
            today = date.today()
        qs = self.current(today)
        qs = self.filter(weekday=today.weekday())
        filters = []
        # week periods
        for week_period in range(1,5):
            filters.append(models.Q(week_period=week_period,
                week_offset=weeks_since_epoch(today) % week_period))
        # week parity
        parity = (today.isocalendar()[1]-1) % 2
        filters.append(models.Q(week_parity=parity))
        # week ranks
        filters.append(models.Q(week_rank__in=weekday_ranks(today)))
        qs = qs.filter(reduce(models.Q.__or__, filters))
        return qs

PERIODICITIES = (
        (1, u'Toutes les semaines'),
        (2, u'Une semaine sur deux'),
        (3, u'Une semaine sur trois'),
        (4, u'Une semaine sur quatre'),
        (5, u'Une semaine sur cinq'),
        (6, u'La première semaine du mois'),
        (7, u'La deuxième semaine du mois'),
        (8, u'La troisième semaine du mois'),
        (9, u'La quatrième semaine du mois'),
        (10, u'La dernière semaine du mois'),
        (11, u'Les semaines paires'),
        (12, u'Les semaines impaires')
)


class TimeTable(BaseModelMixin, models.Model):
    objects = PassThroughManager.for_queryset_class(TimeTableQuerySet)()
    worker = models.ForeignKey(Worker,
            verbose_name=u'Intervenant')
    services = models.ManyToManyField('ressources.Service')
    WEEKDAYS = Choices(*enumerate(('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi',
        'samedi', 'dimanche')))

    weekday = models.PositiveIntegerField(
        verbose_name=u"Jour de la semaine",
        choices=WEEKDAYS)
    start_time = models.TimeField(
        verbose_name=u'Heure de début')
    end_time = models.TimeField(
        verbose_name=u'Heure de fin')
    start_date = models.DateField(
        verbose_name=u'Début',
        help_text=u'format: jj/mm/aaaa')
    end_date = models.DateField(
        verbose_name=u'Fin', blank=True, null=True,
        help_text=u'format: jj/mm/aaaa')

    periodicity = models.PositiveIntegerField(
            choices=PERIODICITIES,
            verbose_name=u"Périodicité",
            default=1,
            blank=True,
            null=True)

    PERIODS = (
            (1, u'Toutes les semaines'),
            (2, u'Une semaine sur deux'),
            (3, u'Une semaine sur trois'),
            (4, u'Une semaine sur quatre'),
            (5, u'Une semaine sur cinq')
    )
    OFFSET = range(0,4)
    week_offset = models.PositiveIntegerField(
            choices=zip(OFFSET, OFFSET),
            verbose_name=u"Décalage en semaines par rapport au 1/1/1970 pour le calcul de période",
            default=0)
    week_period = models.PositiveIntegerField(
            choices=PERIODS,
            verbose_name=u"Période en semaines",
            blank=True, null=True)

    PARITIES = (
            (0, u'Les semaines paires'),
            (1, u'Les semaines impaires')
    )
    week_parity = models.PositiveIntegerField(
            choices=PARITIES,
            verbose_name=u"Parité des semaines",
            blank=True, null=True)

    WEEK_RANKS = (
            (0, u'La première semaine du mois'),
            (1, u'La deuxième semaine du mois'),
            (2, u'La troisième semaine du mois'),
            (3, u'La quatrième semaine du mois'),
            (4, u'La dernière semaine du mois')
    )

    week_rank = models.PositiveIntegerField(
            verbose_name=u"Rang de la semaine dans le mois",
            choices=WEEK_RANKS,
            blank=True, null=True)

    def clean(self):
        if (self.week_period is None) + (self.week_parity is None) + \
                (self.week_rank is None) != 2:
            raise forms.ValidationError('Only one periodicity criteria can be used')
        if self.week_period and self.start_date:
            self.week_offset = weeks_since_epoch(self.start_date) % self.week_period

    def __unicode__(self):
        s = u'%s pour au %s le %s de %s à %s' % \
                (self.worker, ', '.join(map(unicode, self.services.all())), self.weekday, self.start_time,
                        self.end_time)
        if self.end_time:
            s += u' à partir du %s' % self.start_date
        else:
            s += u' du %s au %s' % (self.start_data, self.end_date)
        return s

    class Meta:
        verbose_name = u'Emploi du temps'
        verbose_name_plural = u'Emplois du temps'

    def to_interval(self, date):
        return Interval(datetime.combine(date, self.start_time),
                datetime.combine(date, self.end_time))

class HolidayQuerySet(query.QuerySet):
    # To grab group holidays:
    # No worker AND
    # Either the holiday has no service, that means for all
    # Or the user must be in the service of the holiday
    def for_worker(self, worker):
        filter_query = models.Q(worker=worker) \
              | models.Q(worker__isnull=True,
                           service=None) \
              | models.Q(worker__isnull=True,
                           service__in=worker.services.all())
        return self.filter(filter_query)

    def for_worker_id(self, worker_id):
        worker = None
        try:
            worker = Worker.objects.get(pk=worker_id)
        except:
            return None
        filter_query = models.Q(worker=worker) \
              | models.Q(worker__isnull=True,
                           service=None) \
              | models.Q(worker__isnull=True,
                           service__in=worker.services.all())
        return self.filter(filter_query)

    def for_type(self, holiday_type):
        return self.filter(holiday_type=holiday_type)

    def for_service(self, service):
        return self.filter(worker__isnull=True) \
                   .filter(models.Q(service=service)
                          |models.Q(service__isnull=True))

    def for_service_workers(self, service):
        return self.filter(worker__services=service)

    def future(self):
        return self.filter(end_date__gte=date.today())

    def today(self):
        today = date.today()
        return self.filter(start_date__lte=today,
                end_date__gte=today)

    def for_period(self, start_date, end_date):
        return self.filter(start_date__lte=end_date, end_date__gte=start_date)

def time2french(time):
    if time.minute:
        return '{0}h{1}'.format(time.hour, time.minute)
    return '{0}h'.format(time.hour)

class Holiday(BaseModelMixin, models.Model):
    objects = PassThroughManager().for_queryset_class(HolidayQuerySet)()

    holiday_type = models.ForeignKey('ressources.HolidayType',
            verbose_name=u'Type de congé')
    worker = models.ForeignKey(Worker, blank=True, null=True,
            verbose_name=u"Personnel")
    service = models.ForeignKey(Service, blank=True, null=True,
            verbose_name=u"Service")
    start_date = models.DateField(verbose_name=u"Date de début",
        help_text=u'format: jj/mm/aaaa')
    end_date = models.DateField(verbose_name=u"Date de fin",
        help_text=u'format: jj/mm/aaaa')
    start_time = models.TimeField(verbose_name=u"Horaire de début", blank=True,
            null=True)
    end_time = models.TimeField(verbose_name=u"Horaire de fin", blank=True,
            null=True)
    comment = models.TextField(verbose_name=u'Commentaire', blank=True)

    class Meta:
        verbose_name = u'Congé'
        verbose_name_plural = u'Congés'
        ordering = ('start_date', 'start_time')

    def is_current(self):
        return self.start_date <= date.today() <= self.end_date

    def __unicode__(self):
        ret = ''
        if self.start_date == self.end_date:
            ret = u'le {0}'.format(date_filter(self.start_date, 'j F Y'))
            if self.start_time:
                ret += u', à partir de {0}'.format(time2french(self.start_time))
            if self.end_time:
                ret += u", jusqu'à {0}".format(time2french(self.end_time))
        else:
            ret = u'du {0}'.format(date_filter(self.start_date, 'j F Y'))
            if self.start_time:
                ret += u' (à partir de {0})'.format(time2french(self.start_time))
            ret += u' au {0}'.format(date_filter(self.end_date, 'j F Y'))
            if self.end_time:
                ret += u" (jusqu'à {0})".format(time2french(self.end_time))
        return ret

    def to_interval(self, date):
        if date == self.start_date:
            start_time = self.start_time or datetime_time(8, 0)
        else:
            start_time = datetime_time(8, 0)
        if date == self.end_date:
            end_time = self.end_time or datetime_time(20, 0)
        else:
            end_time = datetime_time(20, 0)
        return Interval(datetime.combine(self.start_date, start_time),
                datetime.combine(self.end_date, end_time))


class ExternalDoctor(People):
    class Meta:
        verbose_name = u'Médecin extérieur'
        verbose_name_plural = u'Médecins extérieurs'

class ExternalIntervener(People):
    class Meta:
        verbose_name = u'Intervenant extérieur'
        verbose_name_plural = u'Intervenants extérieurs'
