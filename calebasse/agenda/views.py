# -*- coding: utf-8 -*-

import datetime

from django.db.models import Q
from django.shortcuts import redirect
from django.http import HttpResponseRedirect

from calebasse.cbv import TemplateView, CreateView, UpdateView
from calebasse.agenda.models import Occurrence, Event, EventType
from calebasse.personnes.models import TimeTable
from calebasse.actes.models import EventAct
from calebasse.agenda.appointments import get_daily_appointments
from calebasse.personnes.models import Worker
from calebasse.ressources.models import WorkerType
from calebasse.actes.validation import get_acts_of_the_day
from calebasse.actes.validation_states import VALIDATION_STATES
from calebasse.actes.models import Act, ValidationMessage
from calebasse.actes.validation import (automated_validation,
    unlock_all_acts_of_the_day, are_all_acts_of_the_day_locked)
from calebasse import cbv

from forms import (NewAppointmentForm, NewEventForm,
        UpdateAppointmentForm, UpdateEventForm)

def redirect_today(request, service):
    '''If not date is given we redirect on the agenda for today'''
    return redirect('agenda', date=datetime.date.today().strftime('%Y-%m-%d'),
            service=service)

class AgendaHomepageView(TemplateView):

    template_name = 'agenda/index.html'

    def get_context_data(self, **kwargs):
        context = super(AgendaHomepageView, self).get_context_data(**kwargs)

        time_tables = TimeTable.objects.select_related('worker'). \
                filter(services=self.service). \
                for_today(self.date). \
                order_by('start_date')
        occurrences = Occurrence.objects.daily_occurrences(context['date']).order_by('start_time')

        context['workers_types'] = []
        context['workers_agenda'] = []
        context['disponibility'] = {}
        workers = []
        for worker_type in WorkerType.objects.all():
            workers_type = Worker.objects.for_service(self.service, worker_type)
            if workers_type:
                data = {'type': worker_type.name, 'workers': workers_type }
                context['workers_types'].append(data)
                workers.extend(data['workers'])

        occurrences_workers = {}
        time_tables_workers = {}
        for worker in workers:
            time_tables_worker = [tt for tt in time_tables if tt.worker.id == worker.id]
            occurrences_worker = [o for o in occurrences if worker.id in o.event.participants.values_list('id', flat=True)]
            occurrences_workers[worker.id] = occurrences_worker
            time_tables_workers[worker.id] = time_tables_worker
            context['workers_agenda'].append({'worker': worker,
                    'appointments': get_daily_appointments(context['date'], worker, self.service,
                        time_tables_worker, occurrences_worker)})

        context['disponibility'] = Occurrence.objects.daily_disponiblity(context['date'],
                occurrences_workers, workers, time_tables_workers)
        return context

class AgendaServiceActivityView(TemplateView):

    template_name = 'agenda/service-activity.html'

    def get_context_data(self, **kwargs):
        context = super(AgendaServiceActivityView, self).get_context_data(**kwargs)

        appointments_times = dict()
        appoinment_type = EventType.objects.get(id=1)
        occurrences = Occurrence.objects.daily_occurrences(context['date'],
                services=[self.service],
                event_type=appoinment_type)
        for occurrence in occurrences:
            start_time = occurrence.start_time.strftime("%H:%M")
            if not appointments_times.has_key(start_time):
                appointments_times[start_time] = dict()
                appointments_times[start_time]['row'] = 0
                appointments_times[start_time]['appointments'] = []
            appointment = dict()
            length = occurrence.end_time - occurrence.start_time
            if length.seconds:
                length = length.seconds / 60
                appointment['length'] = "%sm" % length
            event_act = occurrence.event.eventact
            appointment['patient'] = event_act.patient.display_name
            appointment['therapists'] = ""
            for participant in occurrence.event.participants.all():
                appointment['therapists'] += participant.display_name + "; "
            if appointment['therapists']:
                appointment['therapists'] = appointment['therapists'][:-2]
            appointment['act'] = event_act.act_type.name
            appointments_times[start_time]['row'] += 1
            appointments_times[start_time]['appointments'].append(appointment)
        context['appointments_times'] = sorted(appointments_times.items())
        return context


class NewAppointmentView(cbv.ReturnToObjectMixin, cbv.ServiceFormMixin, CreateView):
    model = EventAct
    form_class = NewAppointmentForm
    template_name = 'agenda/nouveau-rdv.html'
    success_url = '..'

    def get_initial(self):
        initial = super(NewAppointmentView, self).get_initial()
        initial['date'] = self.date
        initial['participants'] = self.request.GET.getlist('participants')
        initial['time'] = self.request.GET.get('time')
        return initial


class UpdateAppointmentView(UpdateView):
    model = EventAct
    form_class = UpdateAppointmentForm
    template_name = 'agenda/update-rdv.html'
    success_url = '..'

    def get_object(self, queryset=None):
        self.occurrence = Occurrence.objects.get(id=self.kwargs['id'])
        if self.occurrence.event.eventact:
            return self.occurrence.event.eventact

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial['date'] = self.object.date
        initial['time'] = self.occurrence.start_time.strftime("%H:%M")
        time = self.occurrence.end_time - self.occurrence.start_time
        if time:
            time = time.seconds / 60
        else:
            time = 0
        initial['duration'] = time
        initial['participants'] = self.object.participants.values_list('id', flat=True)
        return initial

    def get_form_kwargs(self):
        kwargs = super(UpdateAppointmentView, self).get_form_kwargs()
        kwargs['occurrence'] = self.occurrence
        return kwargs


class NewEventView(CreateView):
    model = Event
    form_class = NewEventForm
    template_name = 'agenda/new-event.html'
    success_url = '..'

    def get_initial(self):
        initial = super(NewEventView, self).get_initial()
        initial['date'] = self.date
        initial['participants'] = self.request.GET.getlist('participants')
        initial['time'] = self.request.GET.get('time')
        initial['services'] = [self.service]
        initial['event_type'] = 2
        return initial

class UpdateEventView(UpdateView):
    model = Event
    form_class = UpdateEventForm
    template_name = 'agenda/update-event.html'
    success_url = '..'

    def get_object(self, queryset=None):
        self.occurrence = Occurrence.objects.get(id=self.kwargs['id'])
        return self.occurrence.event

    def get_initial(self):
        initial = super(UpdateEventView, self).get_initial()
        initial['date'] = self.occurrence.start_time.strftime("%Y-%m-%d")
        initial['time'] = self.occurrence.start_time.strftime("%H:%M")
        time = self.occurrence.end_time - self.occurrence.start_time
        if time:
            time = time.seconds / 60
        else:
            time = 0
        initial['duration'] = time
        initial['participants'] = self.object.participants.values_list('id', flat=True)
        return initial

    def get_form_kwargs(self):
        kwargs = super(UpdateEventView, self).get_form_kwargs()
        kwargs['occurrence'] = self.occurrence
        return kwargs

def new_appointment(request):
    pass

class AgendaServiceActValidationView(TemplateView):

    template_name = 'agenda/act-validation.html'

    def acts_of_the_day(self):
        return get_acts_of_the_day(self.date, self.service)

    def post(self, request, *args, **kwargs):
        if 'unlock-all' in request.POST:
            #TODO: check that the user is authorized
            unlock_all_acts_of_the_day(self.date, self.service)
            ValidationMessage(validation_date=self.date,
                who=request.user, what='Déverrouillage',
                service=self.service).save()
        else:
            acte_id = request.POST.get('acte-id')
            try:
                act = Act.objects.get(id=acte_id)
                if 'lock' in request.POST or 'unlock' in request.POST:
                    #TODO: check that the user is authorized
                    act.validation_locked = 'lock' in request.POST
                    act.save()
                else:
                    state_name = request.POST.get('act_state')
                    act.set_state(state_name, request.user)
            except Act.DoesNotExist:
                pass
            return HttpResponseRedirect('#acte-frame-'+acte_id)
        return HttpResponseRedirect('')

    def get_context_data(self, **kwargs):
        context = super(AgendaServiceActValidationView, self).get_context_data(**kwargs)
        authorized_lock = True # is_authorized_for_locking(get_request().user)
        validation_msg = ValidationMessage.objects.\
            filter(validation_date=self.date, service=self.service).\
            order_by('-when')[:3]
        acts_of_the_day = self.acts_of_the_day()
        actes = list()
        for act in acts_of_the_day:
            state = act.get_state()
            display_name = VALIDATION_STATES[state.state_name]
            if not state.previous_state:
                state = None
            act.date = act.date.strftime("%H:%M")
            actes.append((act, state, display_name))
        context['validation_states'] = VALIDATION_STATES
        context['actes'] = actes
        context['validation_msg'] = validation_msg
        context['authorized_lock'] = authorized_lock
        return context


class AutomatedValidationView(TemplateView):
    template_name = 'agenda/automated-validation.html'

    def post(self, request, *args, **kwargs):
        automated_validation(self.date, self.service,
            request.user)
        ValidationMessage(validation_date=self.date,
            who=request.user, what='Validation automatique',
            service=self.service).save()
        return HttpResponseRedirect('..')

    def get_context_data(self, **kwargs):
        context = super(AutomatedValidationView, self).get_context_data(**kwargs)
        request = self.request
        (nb_acts_total, nb_acts_validated, nb_acts_double,
            nb_acts_abs_non_exc, nb_acts_abs_exc, nb_acts_annul_nous,
            nb_acts_annul_famille, nb_acts_abs_ess_pps,
            nb_acts_enf_hosp) = \
            automated_validation(self.date, self.service,
                request.user, commit = False)

        nb_acts_not_validated = nb_acts_double + \
            nb_acts_abs_non_exc + \
            nb_acts_abs_exc + \
            nb_acts_annul_nous + \
            nb_acts_annul_famille + \
            nb_acts_abs_ess_pps + \
            nb_acts_enf_hosp
        context.update({
            'nb_acts_total': nb_acts_total,
            'nb_acts_validated': nb_acts_validated,
            'nb_acts_not_validated': nb_acts_not_validated,
            'nb_acts_double': nb_acts_double,
            'nb_acts_abs_non_exc': nb_acts_abs_non_exc,
            'nb_acts_abs_exc': nb_acts_abs_exc,
            'nb_acts_annul_nous': nb_acts_annul_nous,
            'nb_acts_annul_famille': nb_acts_annul_famille,
            'nb_acts_abs_ess_pps': nb_acts_abs_ess_pps,
            'nb_acts_enf_hosp': nb_acts_enf_hosp})
        return context

class UnlockAllView(CreateView):
    pass


class AgendasTherapeutesView(AgendaHomepageView):

    template_name = 'agenda/agendas-therapeutes.html'

    def get_context_data(self, **kwargs):
        context = super(AgendasTherapeutesView, self).get_context_data(**kwargs)
        for worker_agenda in context.get('workers_agenda', []):
            patient_appointments = [x for x in worker_agenda['appointments'] if x.patient_record_id]
            worker_agenda['summary'] = {
              'rdv': len(patient_appointments),
              'presence': len([x for x in patient_appointments if x.act_absence is None]),
              'absence': len([x for x in patient_appointments if x.act_absence is not None]),
              'doubles': len([x for x in patient_appointments if x.act_type == 'ACT_DOUBLE']),
              'valides': len([x for x in patient_appointments if x.act_type == 'ACT_VALIDE']),
            }

        return context

class JoursNonVerrouillesView(TemplateView):

    template_name = 'agenda/days-not-locked.html'

    def get_context_data(self, **kwargs):
        context = super(JoursNonVerrouillesView, self).get_context_data(**kwargs)
        acts = EventAct.objects.filter(is_billed=False,
            patient__service=self.service).order_by('date')
        days_not_locked = []
        for act in acts:
            current_day = datetime.datetime(act.date.year, act.date.month, act.date.day)
            if not current_day in days_not_locked:
                locked = are_all_acts_of_the_day_locked(current_day, self.service)
                if not locked:
                    days_not_locked.append(current_day)
        context['days_not_locked'] = days_not_locked
        return context

