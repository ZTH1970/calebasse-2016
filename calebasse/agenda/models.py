# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from copy import copy

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db import models
from django import forms

from calebasse.agenda import managers
from calebasse.utils import weeks_since_epoch, weekday_ranks
from interval import Interval

__all__ = (
    'EventType',
    'Event',
    'EventWithAct',
)

class EventType(models.Model):
    '''
    Simple ``Event`` classifcation.
    '''
    class Meta:
        verbose_name = u'Type d\'événement'
        verbose_name_plural = u'Types d\'événement'

    def __unicode__(self):
        return self.label

    label = models.CharField(_('label'), max_length=50)
    rank = models.IntegerField(_('Sorting Rank'), null=True, blank=True, default=0)

class Event(models.Model):
    '''
    Container model for general agenda events
    '''
    objects = managers.EventManager()

    title = models.CharField(_('Title'), max_length=32, blank=True)
    description = models.TextField(_('Description'), max_length=100)
    event_type = models.ForeignKey(EventType, verbose_name=u"Type d'événement")
    creator = models.ForeignKey(User, verbose_name=_(u'Créateur'), blank=True, null=True)
    create_date = models.DateTimeField(_(u'Date de création'), auto_now_add=True)

    services = models.ManyToManyField('ressources.Service',
            null=True, blank=True, default=None)
    participants = models.ManyToManyField('personnes.People',
            null=True, blank=True, default=None)
    room = models.ForeignKey('ressources.Room', blank=True, null=True,
            verbose_name=u'Salle')

    start_datetime = models.DateTimeField(_('Début'), db_index=True)
    end_datetime = models.DateTimeField(_('Fin'), blank=True, null=True)
    old_ev_id = models.CharField(max_length=8, blank=True, null=True)
    old_rr_id = models.CharField(max_length=8, blank=True, null=True)
    # only used when there is no rr id
    old_rs_id = models.CharField(max_length=8, blank=True, null=True)
    # exception to is mutually exclusive with recurrence_periodicity
    # an exception cannot be periodic
    exception_to = models.ForeignKey('self', related_name='exceptions',
            blank=True, null=True,
            verbose_name=u'Exception à')
    exception_date = models.DateField(blank=True, null=True,
            verbose_name=u'Reporté du')
    # canceled can only be used with exception to
    canceled = models.BooleanField(_('Annulé'))

    PERIODS = (
            (1, u'Toutes les semaines'),
            (2, u'Une semaine sur deux'),
            (3, u'Une semaine sur trois'),
            (4, 'Une semaine sur quatre'),
            (5, 'Une semaine sur cinq')
    )
    OFFSET = range(0,4)
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
    WEEK_RANKS = (
            (0, u'La première semaine du mois'),
            (1, u'La deuxième semaine du mois'),
            (2, u'La troisième semaine du mois'),
            (3, u'La quatrième semaine du mois'),
            (4, u'La dernière semaine du mois')
    )
    PARITIES = (
            (0, u'Les semaines paires'),
            (1, u'Les semaines impaires')
    )
    recurrence_periodicity = models.PositiveIntegerField(
            choices=PERIODICITIES,
            verbose_name=u"Périodicité",
            default=None,
            blank=True,
            null=True)
    recurrence_week_day = models.PositiveIntegerField(default=0)
    recurrence_week_offset = models.PositiveIntegerField(
            choices=zip(OFFSET, OFFSET),
            verbose_name=u"Décalage en semaines par rapport au 1/1/1970 pour le calcul de période",
            default=0,
            db_index=True)
    recurrence_week_period = models.PositiveIntegerField(
            choices=PERIODS,
            verbose_name=u"Période en semaines",
            default=None,
            blank=True,
            null=True,
            db_index=True)
    recurrence_week_rank = models.PositiveIntegerField(
            verbose_name=u"Rang de la semaine dans le mois",
            choices=WEEK_RANKS,
            blank=True, null=True)
    recurrence_week_parity = models.PositiveIntegerField(
            choices=PARITIES,
            verbose_name=u"Parité des semaines",
            blank=True,
            null=True)
    recurrence_end_date = models.DateField(
            verbose_name=_(u'Fin de la récurrence'),
            blank=True, null=True,
            db_index=True)

    PERIOD_LIST_TO_FIELDS = [(1, None, None),
        (2, None, None),
        (3, None, None),
        (4, None, None),
        (5, None, None),
        (None, 0, None),
        (None, 1, None),
        (None, 2, None),
        (None, 3, None),
        (None, 4, None),
        (None, None, 0),
        (None, None, 1)
    ]

    class Meta:
        verbose_name = u'Evénement'
        verbose_name_plural = u'Evénements'
        ordering = ('start_datetime', 'end_datetime', 'title')
        unique_together = (('exception_to', 'exception_date'),)

    def __init__(self, *args, **kwargs):
        if kwargs.get('start_datetime') and not kwargs.has_key('recurrence_end_date'):
            kwargs['recurrence_end_date'] = kwargs.get('start_datetime').date()
        super(Event, self).__init__(*args, **kwargs)

    def clean(self):
        '''Initialize recurrence fields if they are not.'''
        if self.recurrence_periodicity:
            l = self.PERIOD_LIST_TO_FIELDS[self.recurrence_periodicity-1]
        else:
            l = None, None, None
        self.recurrence_week_period = l[0]
        self.recurrence_week_rank = l[1]
        self.recurrence_week_parity = l[2]
        if self.recurrence_periodicity:
            if self.recurrence_end_date and self.recurrence_end_date < self.start_datetime.date():
                raise forms.ValidationError(u'La date de fin de périodicité doit être postérieure à la date de début.')
            if self.start_datetime:
                self.recurrence_week_day = self.start_datetime.weekday()
        if self.recurrence_week_period is not None:
            if self.start_datetime:
                self.recurrence_week_offset = weeks_since_epoch(self.start_datetime) % self.recurrence_week_period
        if self.recurrence_week_parity is not None:
            if self.start_datetime:
                week = self.start_datetime.date().isocalendar()[1]
                start_week_parity = week % 2
                if start_week_parity != self.recurrence_week_parity:
                    raise forms.ValidationError(u'Le date de départ de la périodicité est en semaine {week}.'.format(week=week))
        if self.recurrence_week_rank is not None and self.start_datetime:
            start_week_ranks = weekday_ranks(self.start_datetime.date())
            if self.recurrence_week_rank not in start_week_ranks:
                raise forms.ValidationError('La date de début de périodicité doit faire partie de la bonne semaine dans le mois.')

    def timedelta(self):
        '''Distance between start and end of the event'''
        return self.end_datetime - self.start_datetime

    def match_date(self, date):
        if self.is_recurring():
            # consider exceptions
            exception = self.get_exceptions_dict().get(date)
            if exception is not None:
                return exception if exception.match_date(date) else None
            if self.canceled:
                return None
            if date.weekday() != self.recurrence_week_day:
                return None
            if self.start_datetime.date() > date:
                return None
            if self.recurrence_end_date and self.recurrence_end_date < date:
                return None
            if self.recurrence_week_period is not None:
                if weeks_since_epoch(date) % self.recurrence_week_period != self.recurrence_week_offset:
                    return None
            elif self.recurrence_week_parity is not None:
                if date.isocalendar()[1] % 2 != self.recurrence_week_parity:
                    return None
            elif self.recurrence_week_rank is not None:
                if self.recurrence_week_rank not in weekday_ranks(date):
                    return None
            else:
                raise NotImplemented
            return self
        else:
            return date == self.start_datetime.date()


    def today_occurrence(self, today=None, match=False):
        '''For a recurring event compute the today 'Event'.

           The computed event is the fake one that you cannot save to the database.
        '''
        today = today or date.today()
        if self.canceled:
            return None
        if match:
            exception = self.get_exceptions_dict().get(today)
            if exception and exception.start_datetime.date() == today():
                return exception.today_occurrence(today, True)
            else:
                return None
        else:
            exception_or_self = self.match_date(today)
            if exception_or_self is None:
                return None
            if exception_or_self != self:
                return exception_or_self.today_occurrence(today)
        start_datetime = datetime.combine(today, self.start_datetime.timetz())
        end_datetime = start_datetime + self.timedelta()
        event = copy(self)
        event.exception_to = self
        event.exception_date = today
        event.start_datetime = start_datetime
        event.end_datetime = end_datetime
        event.recurrence_periodicity = None
        event.recurrence_week_offset = 0
        event.recurrence_week_period = None
        event.recurrence_week_parity = None
        event.recurrence_week_rank = None
        event.recurrence_end_date = None
        event.parent = self
        # the returned event is "virtual", it must not be saved
        old_save = event.save
        old_participants = list(self.participants.all())
        def save(*args, **kwargs): 
            event.id = None
            old_save(*args, **kwargs)
            event.participants = old_participants
        event.save = save
        return event

    def next_occurence(self, today=None):
        '''Returns the next occurence after today.'''
        today = today or date.today()
        for occurence in self.all_occurences():
            if occurence.start_datetime.date() > today:
                return occurence

    def is_recurring(self):
        '''Is this event multiple ?'''
        return self.recurrence_periodicity is not None

    def get_exceptions_dict(self):
        if not hasattr(self, 'exceptions_dict'):
            self.exceptions_dict = dict()
            for exception in self.exceptions.all():
                self.exceptions_dict[exception.exception_date] = exception
        return self.exceptions_dict

    def all_occurences(self, limit=90):
        '''Returns all occurences of this event as virtual Event objects

           limit - compute occurrences until limit days in the future

           Default is to limit to 90 days.
        '''
        if self.recurrence_periodicity is not None:
            day = self.start_datetime.date()
            max_end_date = max(date.today(), self.start_datetime.date()) + timedelta(days=limit)
            end_date = min(self.recurrence_end_date or max_end_date, max_end_date)
            occurrences = []
            if self.recurrence_week_period is not None:
                delta = timedelta(days=self.recurrence_week_period*7)
                while day <= end_date:
                    occurrence = self.today_occurrence(day)
                    if occurrence is not None:
                        occurrences.append(occurrence)
                    day += delta
            elif self.recurrence_week_parity is not None:
                delta = timedelta(days=7)
                while day <= end_date:
                    if day.isocalendar()[1] % 2 == self.recurrence_week_parity:
                        if occurrence is not None:
                            occurrences.append(occurrence)
                    day += delta
            elif self.recurrence_week_rank is not None:
                delta = timedelta(days=7)
                while day <= end_date:
                    if self.recurrence_week_rank in weekday_ranks(day):
                        if occurrence is not None:
                            occurrences.append(occurrence)
                    day += delta
            for exception in self.exceptions.all():
                if exception.exception_date != exception.start_datetime.date():
                    occurrences.append(exception)
            return sorted(occurrences, key=lambda o: o.start_datetime)
        else:
            return [self]

    def save(self, *args, **kwargs):
        assert self.recurrence_periodicity is None or self.exception_to is None
        self.clean() # force call to clean to initialize recurrence fields
        super(Event, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # never delete, only cancel
        from ..actes.models import Act
        for a in Act.objects.filter(parent_event=self):
            if len(a.actvalidationstate_set.all()) > 1:
                a.parent_event = None
                a.save()
            else:
                a.delete()
        self.canceled = True
        self.save()

    def to_interval(self):
        return Interval(self.start_datetime, self.end_datetime)

    def is_event_absence(self):
        return False

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return '<Event: on {start_datetime} with {participants}'.format(
                start_datetime=self.start_datetime,
                participants=self.participants.all() if self.id else '<un-saved>')


class OldRSID(models.Model):
    event = models.ForeignKey(Event)
    old_rs_id = models.CharField(max_length=8, blank=True, null=True)


class EventWithActManager(managers.EventManager):
    def create_patient_appointment(self, creator, title, patient,
            doctors=[], act_type=None, service=None, start_datetime=None, end_datetime=None,
            room=None, periodicity=1, until=False):
        appointment = self.create_event(creator=creator,
                title=title,
                event_type=EventType(id=1),
                participants=doctors,
                services=[service],
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                room=room,
                periodicity=periodicity,
                until=until,
                act_type=act_type,
                patient=patient)
        return appointment


class EventWithAct(Event):
    '''An event corresponding to an act.'''
    objects = EventWithActManager()
    act_type = models.ForeignKey('ressources.ActType',
        verbose_name=u'Type d\'acte')
    patient = models.ForeignKey('dossiers.PatientRecord')
    convocation_sent = models.BooleanField(blank=True,
        verbose_name=u'Convoqué')


    def delete(self, *args, **kwargs):
        if self.recurrence_periodicity is None:
            # clear all linked exceptions
            pass
        elif self.exception_to is not None:
            pass
        elif hasattr(self, 'parent'):
            pass
        else:
            # clear all linked exceptions
            pass
        super(EventWithAct, self).delete(*args, **kwargs)

    @property
    def act(self):
        return self.get_or_create_act()

    def get_or_create_act(self, today=None):
        from ..actes.models import Act, ActValidationState
        today = today or self.start_datetime.date()
        act, created = Act.objects.get_or_create(patient=self.patient,
                parent_event=getattr(self, 'parent', self),
                date=today,
                act_type=self.act_type)
        self.update_act(act)
        if created:
            ActValidationState.objects.create(act=act, state_name='NON_VALIDE',
                author=self.creator, previous_state=None)
        return act

    def update_act(self, act):
        '''Update an act to match details of the meeting'''
        delta = self.timedelta()
        duration = delta.seconds // 60
        act._duration = duration
        act.doctors = self.participants.select_subclasses()
        act.act_type = self.act_type
        act.patient = self.patient
        act.date = self.start_datetime.date()
        act.save()

    def save(self, *args, **kwargs):
        '''Force event_type to be patient meeting.'''
        self.event_type = EventType(id=1)
        super(EventWithAct, self).save(*args, **kwargs)
        # list of occurences may have changed
        from ..actes.models import Act
        occurences = list(self.all_occurences())
        acts = Act.objects.filter(parent_event=self)
        occurences_by_date = dict((o.start_datetime.date(), o) for o in occurences)
        acts_by_date = dict()
        for a in acts:
            # sanity check
            assert a.date not in acts_by_date
            acts_by_date[a.date] = a
        for a in acts:
            o = occurences_by_date.get(a.date)
            if o:
                o.update_act(a)
            else:
                if len(a.actvalidationstate_set.all()) > 1:
                    a.parent_event = None
                    a.save()
                else:
                    a.delete()
        for o in occurences:
            if o.start_datetime.date() in acts_by_date:
                continue
            o.get_or_create_act()

    def is_event_absence(self):
        return self.act.is_absent()

    def __unicode__(self):
        kwargs = {
                'patient': self.patient,
                'start_datetime': self.start_datetime,
                'act_type': self.act_type
        }
        kwargs['doctors'] = ', '.join(map(unicode, self.participants.all())) if self.id else ''
        return u'Rdv le {start_datetime} de {patient} avec {doctors} pour ' \
            '{act_type} ({act_type.id})'.format(**kwargs)


from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender=Event.participants.through)
def participants_changed(sender, instance, action, **kwargs):
    if action.startswith('post'):
        workers = [ p.worker for p in instance.participants.prefetch_related('worker') ]
        for act in instance.act_set.all():
            act.doctors = workers
