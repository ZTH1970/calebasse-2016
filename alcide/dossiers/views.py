# -*- coding: utf-8 -*-

import os

from datetime import datetime, date

from django.conf import settings
from django.db import models
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import View
from django.views.generic.edit import DeleteView
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files import File
from django.forms import Form
from django.utils import formats
from django.shortcuts import get_object_or_404

from alcide import cbv
from alcide.doc_templates import make_doc_from_template
from alcide.dossiers import forms
from alcide.dossiers.views_utils import get_next_rdv, get_last_rdv, get_status
from alcide.dossiers.transport import render_transport
from alcide.agenda.models import Event, EventWithAct
from alcide.actes.models import Act
from alcide.agenda.appointments import Appointment
from alcide.dossiers.models import (PatientRecord, PatientContact,
        PatientAddress, Status, FileState, create_patient, CmppHealthCareTreatment,
        CmppHealthCareDiagnostic, SessadHealthCareNotification, HealthCare,
        TransportPrescriptionLog, ProtectionState)
from alcide.dossiers.states import STATES_MAPPING, STATES_BTN_MAPPER
from alcide.ressources.models import (Service,
    SocialisationDuration, MDPHRequest, MDPHResponse)
from alcide.facturation.list_acts import list_acts_for_billing_CMPP_per_patient
from alcide.facturation.invoice_header import render_to_pdf_file

from alcide.decorators import validator_only


class NewPatientRecordView(cbv.FormView, cbv.ServiceViewMixin):
    form_class = forms.NewPatientRecordForm
    template_name = 'dossiers/patientrecord_new.html'
    success_url = '..'
    patient = None

    def post(self, request, *args, **kwarg):
        self.user = request.user
        return super(NewPatientRecordView, self).post(request, *args, **kwarg)

    def form_valid(self, form):
        self.patient = create_patient(form.data['first_name'], form.data['last_name'], self.service,
                self.user, date_selected=datetime.strptime(form.data['date_selected'], "%d/%m/%Y"))
        return super(NewPatientRecordView, self).form_valid(form)

    def get_success_url(self):
        return '%s/view' % self.patient.id

new_patient_record = NewPatientRecordView.as_view()

class RecordPatientRecordIdMixing(object):
    def dispatch(self, request, *args, **kwargs):
        self.patientrecord_id = request.session['patientrecord_id'] = int(kwargs['patientrecord_id'])
        return super(RecordPatientRecordIdMixing, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RecordPatientRecordIdMixing, self).get_form_kwargs()
        kwargs['patient'] = PatientRecord.objects.get(id=self.patientrecord_id)
        return kwargs

class NewPatientContactView(RecordPatientRecordIdMixing, cbv.CreateView):
    model = PatientContact
    form_class = forms.PatientContactForm
    template_name = 'dossiers/patientcontact_new.html'
    success_url = '../view#tab=2'

    def get_initial(self):
        initial = super(NewPatientContactView, self).get_initial()
        fields = self.form_class.base_fields.keys()
        for arg in self.request.GET.keys():
            if arg in fields:
                if arg == 'addresses':
                    value = self.request.GET.getlist(arg)
                else:
                    value = self.request.GET.get(arg)
                initial[arg] = value
        if initial:
            if not initial.has_key('addresses'):
                initial['addresses'] = []
            patient = PatientRecord.objects.get(id=self.patientrecord_id)
            addresses = patient.addresses.order_by('-id')
            if addresses:
                initial['addresses'].append(addresses[0].pk)
        return initial

new_patient_contact = NewPatientContactView.as_view()

class UpdatePatientContactView(RecordPatientRecordIdMixing, cbv.NotificationDisplayView, cbv.UpdateView):
    model = PatientContact
    form_class = forms.PatientContactForm
    template_name = 'dossiers/patientcontact_new.html'
    success_url = '../../view#tab=2'

update_patient_contact = UpdatePatientContactView.as_view()

class DeletePatientContactView(cbv.DeleteView):
    model = PatientContact
    form_class = forms.PatientContactForm
    template_name = 'dossiers/patientcontact_confirm_delete.html'
    success_url = '../../view#tab=2'

    def post(self, request, *args, **kwargs):
        try:
            patient = PatientRecord.objects.get(id=kwargs.get('pk'))
        except PatientRecord.DoesNotExist:
            return super(DeletePatientContactView, self).post(request, *args, **kwargs)
        # the contact is also a patient record; it shouldn't be deleted; just
        # altered to remove an address
        patient.addresses.remove(self.request.GET['address'])
        return HttpResponseRedirect(self.get_success_url())

delete_patient_contact = DeletePatientContactView.as_view()

class NewPatientAddressView(cbv.CreateView):
    model = PatientAddress
    form_class = forms.PatientAddressForm
    template_name = 'dossiers/patientaddress_new.html'
    success_url = '../view#tab=2'

    def get_success_url(self):
        return self.success_url

    def form_valid(self, form):
        patientaddress = form.save()
        patientrecord = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        patientrecord.addresses.add(patientaddress)
        messages.add_message(self.request, messages.INFO, u'Nouvelle adresse enregistrée avec succès.')
        return HttpResponseRedirect(self.get_success_url())

new_patient_address = NewPatientAddressView.as_view()

class UpdatePatientAddressView(cbv.NotificationDisplayView, cbv.UpdateView):
    model = PatientAddress
    form_class = forms.PatientAddressForm
    template_name = 'dossiers/patientaddress_new.html'
    success_url = '../../view#tab=2'

update_patient_address = UpdatePatientAddressView.as_view()

class DeletePatientAddressView(cbv.DeleteView):
    model = PatientAddress
    form_class = forms.PatientAddressForm
    template_name = 'dossiers/patientaddress_confirm_delete.html'
    success_url = '../../view#tab=2'

delete_patient_address = DeletePatientAddressView.as_view()


class NewHealthCareView(cbv.CreateView):

    def get_initial(self):
        initial = super(NewHealthCareView, self).get_initial()
        initial['author'] = self.request.user.id
        initial['patient'] = self.kwargs['patientrecord_id']
        return initial

new_healthcare_treatment = \
    NewHealthCareView.as_view(model=CmppHealthCareTreatment,
        template_name = 'dossiers/generic_form.html',
        success_url = '../view#tab=3',
        form_class=forms.CmppHealthCareTreatmentForm)
new_healthcare_diagnostic = \
    NewHealthCareView.as_view(model=CmppHealthCareDiagnostic,
        template_name = 'dossiers/generic_form.html',
        success_url = '../view#tab=3',
        form_class=forms.CmppHealthCareDiagnosticForm)
new_healthcare_notification = \
    NewHealthCareView.as_view(model=SessadHealthCareNotification,
        template_name = 'dossiers/generic_form.html',
        success_url = '../view#tab=3',
        form_class=forms.SessadHealthCareNotificationForm)
update_healthcare_treatment = \
    cbv.UpdateView.as_view(model=CmppHealthCareTreatment,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=3',
        form_class=forms.CmppHealthCareTreatmentForm)
update_healthcare_diagnostic = \
    cbv.UpdateView.as_view(model=CmppHealthCareDiagnostic,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=3',
        form_class=forms.CmppHealthCareDiagnosticForm)
update_healthcare_notification = \
    cbv.UpdateView.as_view(model=SessadHealthCareNotification,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=3',
        form_class=forms.SessadHealthCareNotificationForm)
delete_healthcare_treatment = \
    cbv.DeleteView.as_view(model=CmppHealthCareTreatment,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=3')
delete_healthcare_diagnostic = \
    cbv.DeleteView.as_view(model=CmppHealthCareDiagnostic,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=3')
delete_healthcare_notification = \
    cbv.DeleteView.as_view(model=SessadHealthCareNotification,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=3')


class StateFormView(cbv.FormView):
    template_name = 'dossiers/state.html'
    form_class = forms.StateForm
    success_url = './view#tab=0'


    def post(self, request, *args, **kwarg):
        self.user = request.user
        return super(StateFormView, self).post(request, *args, **kwarg)

    def form_valid(self, form):
        service = Service.objects.get(id=form.data['service_id'])
        status = Status.objects.filter(services=service).filter(type=form.data['state_type'])
        patient = PatientRecord.objects.get(id=form.data['patient_id'])
        date_selected = datetime.strptime(form.data['date'], "%d/%m/%Y")
        patient.set_state(status[0], self.user, date_selected, form.data['comment'])
        return super(StateFormView, self).form_valid(form)

state_form = StateFormView.as_view()

class PatientRecordView(cbv.UpdateView):
    model = PatientRecord
    template_name = 'dossiers/patientrecord_update.html'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordView, self).get_context_data(**kwargs)
        ctx['object'].create_diag_healthcare(self.request.user)
        ctx['object'].automated_switch_state(self.request.user)
        current_state = ctx['object'].get_current_state()
        if not current_state:
            current_state = ctx['object'].get_state()
            ctx['future_state'] = True
        if STATES_MAPPING.has_key(current_state.status.type):
            state = STATES_MAPPING[current_state.status.type]
        else:
            state = current_state.status.name
        ctx['current_state'] = current_state
        ctx['service_id'] = self.service.id
        ctx['states'] = FileState.objects.filter(patient=self.object) \
                .filter(status__services=self.service) \
                .order_by('-date_selected')
        return ctx

patient_record = PatientRecordView.as_view()

class PatientRecordPrint(cbv.DetailView):
    model = PatientRecord
    content_type = 'application/pdf'
    template_name = 'dossiers/patientrecord_print.html'

    def get_context_data(self, *args, **kwargs):
        context = super(PatientRecordPrint, self).get_context_data(*args, **kwargs)
        for view in (PatientRecordGeneralView, PatientRecordAdmView,
                     PatientRecordAddrView, PatientRecordNotifsView, PatientRecordOldActs,
                     PatientRecordNextAppointmentsView, PatientRecordSocialisationView):
            view_instance = view(request=self.request, object=self.object,
                                 service=self.service)
            context.update(view_instance.get_context_data(object=self.object))
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        path = render_to_pdf_file([self.template_name],
                                  self.get_context_data(object = self.object))
        content = File(file(path))
        response = HttpResponse(content, self.content_type)
        response['Content-Length'] = content.size
        output = 'dossier_%s.pdf' % self.object.id
        response['Content-Disposition'] = \
            'attachment; filename="%s"' % output
        return response

patient_record_print = PatientRecordPrint.as_view()

class PatientRecordGeneralView(cbv.UpdateView):
    model = PatientRecord
    form_class = forms.GeneralForm
    template_name = 'dossiers/patientrecord_tab1_general.html'
    success_url = './view'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordGeneralView, self).get_context_data(**kwargs)
        ctx['nb_place_of_lifes'] = ctx['object'].addresses.filter(place_of_life=True).count()
        ctx['initial_state'] = ctx['object'].get_initial_state()
        ctx['last_rdv'] = get_last_rdv(ctx['object'])
        ctx['next_rdv'] = get_next_rdv(ctx['object'])
        current_state = ctx['object'].get_current_state()
        if current_state.status and STATES_MAPPING.has_key(current_state.status.type):
            state = STATES_MAPPING[current_state.status.type]
        elif current_state.status:
            state = current_state.status.name
        else:
            state = "Aucun"
        ctx['current_state'] = current_state
        ctx['status'], ctx['hc_status'] = get_status(ctx, self.request.user)
        ctx['missing_policy'] = False
        if not self.object.policyholder or \
                not self.object.policyholder.health_center or \
                not self.object.policyholder.social_security_id:
            ctx['missing_policy'] = True
        ctx['missing_birthdate'] = False
        if not self.object.birthdate:
            ctx['missing_birthdate'] = True
        return ctx

tab1_general = PatientRecordGeneralView.as_view()

class PatientRecordAdmView(cbv.UpdateView):
    model = PatientRecord
    form_class = forms.AdministrativeForm
    template_name = 'dossiers/patientrecord_tab2_fiche_adm.html'
    success_url = './view#tab=1'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordAdmView, self).get_context_data(**kwargs)
        try:
            ctx['last_prescription'] = TransportPrescriptionLog.objects.filter(patient=ctx['object']).latest('created')
        except:
            pass
        return ctx

tab2_fiche_adm = PatientRecordAdmView.as_view()

class PatientRecordAddrView(cbv.ServiceViewMixin, cbv.NotificationDisplayView, cbv.MultiUpdateView):
    model = PatientRecord
    forms_classes = {
            'contact': forms.PatientContactForm,
            'policyholder': forms.PolicyHolderForm,
            'comment' : forms.AddrCommentForm,
            }
    template_name = 'dossiers/patientrecord_tab3_adresses.html'
    success_url = './view#tab=2'


    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordAddrView, self).get_context_data(**kwargs)
        ctx['nb_place_of_lifes'] = ctx['object'].addresses.filter(place_of_life=True).count()
        ctx['addresses'] = ctx['object'].addresses.order_by('-place_of_life', 'id')
        return ctx

tab3_addresses = PatientRecordAddrView.as_view()

class PatientRecordNotifsView(cbv.DetailView):
    model = PatientRecord
    template_name = 'dossiers/patientrecord_tab4_notifs.html'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordNotifsView, self).get_context_data(**kwargs)
        ctx['status'], ctx['hc_status'] = get_status(ctx, self.request.user)
        if ctx['object'].service.slug == "cmpp":
            (acts_not_locked, days_not_locked, acts_not_valide,
            acts_not_billable, acts_pause, acts_per_hc, acts_losts) = \
                list_acts_for_billing_CMPP_per_patient(self.object,
                    datetime.today(), self.service)
            ctx['acts_losts'] = acts_losts
            ctx['acts_pause'] = acts_pause
            hcs_used = acts_per_hc.keys()
            hcs = None
            if not hcs_used:
                hcs = [(hc, None) for hc in HealthCare.objects.filter(patient=self.object).order_by('-start_date')]
            else:
                hcs = []
                for hc in HealthCare.objects.filter(patient=self.object).order_by('-start_date'):
                    acts = None
                    if hasattr(hc, 'cmpphealthcarediagnostic') and hc.cmpphealthcarediagnostic in hcs_used:
                        acts = acts_per_hc[hc.cmpphealthcarediagnostic]
                    elif hasattr(hc, 'cmpphealthcaretreatment') and hc.cmpphealthcaretreatment in hcs_used:
                        acts = acts_per_hc[hc.cmpphealthcaretreatment]
                    hcs.append((hc, acts))
            ctx['hcs'] = []
            for hc, acts in hcs:
                ctx['hcs'].append((hc, acts, hc.act_set.order_by('date', 'time')))
        elif ctx['object'].service.slug == "sessad-ted" or ctx['object'].service.slug == "sessad-dys":
            ctx['hcs'] = HealthCare.objects.filter(patient=self.object).order_by('-start_date')
        return ctx

tab4_notifs = PatientRecordNotifsView.as_view()

class PatientRecordOldActs(cbv.DetailView):
    model = PatientRecord
    template_name = 'dossiers/patientrecord_tab5_actes_passes.html'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordOldActs, self).get_context_data(**kwargs)
        ctx['last_rdvs'] = []
        for act in Act.objects.last_acts(ctx['object']).prefetch_related('doctors'):
            state = act.get_state()
            if state and not state.previous_state and state.state_name == 'NON_VALIDE':
                state = None
            missing_workers = []
            try:
                missing_workers = [participant.worker for participant in act.event.get_missing_participants()]
            except:
                pass
            ctx['last_rdvs'].append((act, state, missing_workers))
        history = []
        i = 0
        for state in ctx['object'].filestate_set.order_by('-date_selected'):
            acts = []
            try:
                while ctx['last_rdvs'][i][0].date >= state.date_selected.date():
                    acts.append(ctx['last_rdvs'][i])
                    i += 1
            except:
                pass
            history.append((state, acts))
        if i < len(ctx['last_rdvs']) - 1:
            history.append((None, ctx['last_rdvs'][i:]))
        ctx['history'] = history
        return ctx

tab5_old_acts = PatientRecordOldActs.as_view()

class PatientRecordNextAppointmentsView(cbv.DetailView):
    model = PatientRecord
    template_name = 'dossiers/patientrecord_tab6_next_rdv.html'

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordNextAppointmentsView, self).get_context_data(**kwargs)
        ctx['next_rdvs'] = []
        Q = models.Q
        today = date.today()
        qs = EventWithAct.objects.filter(patient=ctx['object']) \
                .filter(exception_to__isnull=True, canceled=False) \
                .filter(Q(start_datetime__gte=today) \
                |  Q(exceptions__isnull=False) \
                | ( Q(recurrence_periodicity__isnull=False) \
                & (Q(recurrence_end_date__gte=today) \
                | Q(recurrence_end_date__isnull=True) \
                ))) \
                .distinct() \
                .select_related() \
                .prefetch_related('participants', 'exceptions__eventwithact',
                        'act_set__actvalidationstate_set')
        occurrences = []
        for event in qs:
            occurrences.extend(filter(lambda e: e.start_datetime.date() >= today,
                event.all_occurences(limit=180)))
        occurrences = sorted(occurrences, key=lambda e: e.start_datetime)
        for event in occurrences:
            state = None
            if event.act:
                state = event.act.get_state()
            if state and not state.previous_state and state.state_name == 'NON_VALIDE':
                state = None
            ctx['next_rdvs'].append((event, state, event.get_missing_participants(), event.get_inactive_participants()))
        return ctx

tab6_next_rdv = PatientRecordNextAppointmentsView.as_view()

class PatientRecordSocialisationView(cbv.DetailView):
    model = PatientRecord
    template_name = 'dossiers/patientrecord_tab7_socialisation.html'

tab7_socialisation = PatientRecordSocialisationView.as_view()

class PatientRecordMedicalView(cbv.UpdateView):
    model = PatientRecord
    form_class = forms.PhysiologyForm
    template_name = 'dossiers/patientrecord_tab8_medical.html'
    success_url = './view#tab=7'

tab8_medical = PatientRecordMedicalView.as_view()

class PatientRecordsHomepageView(cbv.ListView):
    model = PatientRecord
    template_name = 'dossiers/index.html'


    def _get_search_result(self, paginate_patient_records):
        patient_records = []
        for patient_record in paginate_patient_records:
            next_rdv = get_next_rdv(patient_record)
            last_rdv = get_last_rdv(patient_record)
            current_status = patient_record.last_state.status
            state = current_status.name
            state_class = current_status.type.lower()
            patient_records.append(
                    {
                        'object': patient_record,
                        'next_rdv': next_rdv,
                        'last_rdv': last_rdv,
                        'state': state,
                        'state_class': state_class
                        }
                    )
        return patient_records

    def get_queryset(self):
        first_name = self.request.GET.get('first_name')
        last_name = self.request.GET.get('last_name')
        paper_id = self.request.GET.get('paper_id')
        id = self.request.GET.get('id')
        social_security_id = self.request.GET.get('social_security_id')
        if not (first_name or last_name or paper_id or id or social_security_id):
            return None
        if (first_name and len(first_name) < 2) or (last_name and len(last_name) < 2):
            return None
        qs = super(PatientRecordsHomepageView, self).get_queryset()
        states = self.request.GET.getlist('states')
        if last_name:
            qs = qs.filter(last_name__istartswith=last_name)
        if first_name:
            qs = qs.filter(first_name__istartswith=first_name)
        if paper_id:
            qs = qs.filter(paper_id__startswith=paper_id)
        if id:
            qs = qs.filter(id__startswith=id)
        if social_security_id:
            qs = qs.filter(models.Q(social_security_id__startswith=social_security_id) | \
                models.Q(contacts__social_security_id__startswith=social_security_id))
        if states:
            qs = qs.filter(last_state__status__id__in=states)
        else:
            qs = qs.filter(last_state__status__type__in="")
        qs = qs.filter(service=self.service).order_by('last_name').\
                prefetch_related('last_state',
                        'patientcontact', 'last_state__status')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordsHomepageView, self).get_context_data(**kwargs)
        ctx['search_form'] = forms.SearchForm(service=self.service, data=self.request.GET or None)
        ctx['stats'] = [["Dossiers", 0]]
        for status in Status.objects.filter(services=self.service):
            ctx['stats'].append([status.name, 0])

        page = self.request.GET.get('page')
        if ctx['object_list']:
            patient_records = ctx['object_list'].filter()
        else:
            patient_records = []

        # TODO: use a sql query to do this
        for patient_record in patient_records:
            ctx['stats'][0][1] += 1
            for elem in ctx['stats']:
                if elem[0] == patient_record.last_state.status.name:
                    elem[1] += 1
        paginator = Paginator(patient_records, 50)
        try:
            paginate_patient_records = paginator.page(page)
        except PageNotAnInteger:
            paginate_patient_records = paginator.page(1)
        except EmptyPage:
            paginate_patient_records = paginator.page(paginator.num_pages)

        query = self.request.GET.copy()
        if 'page' in query:
            del query['page']
        ctx['query'] = query.urlencode()

        ctx['paginate_patient_records'] = paginate_patient_records
        ctx['patient_records'] = self._get_search_result(paginate_patient_records)
        return ctx

patientrecord_home = PatientRecordsHomepageView.as_view()

class PatientRecordDeleteView(DeleteView):
    model = PatientRecord
    success_url = ".."
    template_name = 'dossiers/patientrecord_confirm_delete.html'

patientrecord_delete = validator_only(PatientRecordDeleteView.as_view())


class PatientRecordPaperIDUpdateView(cbv.UpdateView):
    model = PatientRecord
    form_class = forms.PaperIDForm
    template_name = 'dossiers/generic_form.html'
    success_url = '../view#tab=0'

update_paper_id = PatientRecordPaperIDUpdateView.as_view()


class NewSocialisationDurationView(cbv.CreateView):
    model = SocialisationDuration
    form_class = forms.SocialisationDurationForm
    template_name = 'dossiers/generic_form.html'
    success_url = '../view#tab=6'

    def get_success_url(self):
        return self.success_url

    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(NewSocialisationDurationView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        duration = form.save()
        patientrecord = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        patientrecord.socialisation_durations.add(duration)
        return HttpResponseRedirect(self.get_success_url())

new_socialisation_duration = NewSocialisationDurationView.as_view()

class UpdateSocialisationDurationView(cbv.UpdateView):
    model = SocialisationDuration
    form_class = forms.SocialisationDurationForm
    template_name = 'dossiers/generic_form.html'
    success_url = '../../view#tab=6'

    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(UpdateSocialisationDurationView, self).get(request, *args, **kwargs)

update_socialisation_duration = UpdateSocialisationDurationView.as_view()

class DeleteSocialisationDurationView(cbv.DeleteView):
    model = SocialisationDuration
    form_class = forms.SocialisationDurationForm
    template_name = 'dossiers/socialisationduration_confirm_delete.html'
    success_url = '../../view#tab=6'

delete_socialisation_duration = DeleteSocialisationDurationView.as_view()


class NewMDPHRequestView(cbv.CreateView):
    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(NewMDPHRequestView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        request = form.save()
        patientrecord = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        patientrecord.mdph_requests.add(request)
        return HttpResponseRedirect(self.success_url)

class UpdateMDPHRequestView(cbv.UpdateView):
    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(UpdateMDPHRequestView, self).get(request, *args, **kwargs)


new_mdph_request = \
    NewMDPHRequestView.as_view(model=MDPHRequest,
        template_name = 'dossiers/generic_form.html',
        success_url = '../view#tab=6',
        form_class=forms.MDPHRequestForm)
update_mdph_request = \
    UpdateMDPHRequestView.as_view(model=MDPHRequest,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=6',
        form_class=forms.MDPHRequestForm)
delete_mdph_request = \
    cbv.DeleteView.as_view(model=MDPHRequest,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=6')

class NewMDPHResponseView(cbv.CreateView):
    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(NewMDPHResponseView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        response = form.save()
        patientrecord = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        patientrecord.mdph_responses.add(response)
        return HttpResponseRedirect(self.success_url)

class UpdateMDPHResponseView(cbv.UpdateView):
    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(UpdateMDPHResponseView, self).get(request, *args, **kwargs)


new_mdph_response = \
    NewMDPHResponseView.as_view(model=MDPHResponse,
        template_name = 'dossiers/generic_form.html',
        success_url = '../view#tab=6',
        form_class=forms.MDPHResponseForm)
update_mdph_response = \
    UpdateMDPHResponseView.as_view(model=MDPHResponse,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=6',
        form_class=forms.MDPHResponseForm)
delete_mdph_response = \
    cbv.DeleteView.as_view(model=MDPHResponse,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=6')


class UpdatePatientStateView(cbv.ServiceFormMixin, cbv.UpdateView):

    def get_initial(self):
        initial = super(UpdatePatientStateView, self).get_initial()
        initial['date_selected'] = self.object.date_selected.date()
        return initial

    def get(self, request, *args, **kwargs):
        if kwargs.has_key('patientrecord_id'):
            request.session['patientrecord_id'] = kwargs['patientrecord_id']
        return super(UpdatePatientStateView, self).get(request, *args, **kwargs)

class DeletePatientView(cbv.DeleteView):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object == self.object.patient.last_state:
            status = self.object.patient.filestate_set.all().order_by('-created')
            if len(status) > 1:
                self.object.patient.last_state = status[1]
                self.object.patient.save()
            else:
                # TODO return an error here
                return HttpResponseRedirect(self.get_success_url())
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())


update_patient_state = \
    UpdatePatientStateView.as_view(model=FileState,
        template_name = 'dossiers/generic_form.html',
        success_url = '../../view#tab=0',
        form_class=forms.PatientStateForm)
delete_patient_state = \
    DeletePatientView.as_view(model=FileState,
        template_name = 'dossiers/generic_confirm_delete.html',
        success_url = '../../view#tab=0')


class GenerateRtfFormView(cbv.FormView):
    template_name = 'dossiers/generate_rtf_form.html'
    form_class = forms.GenerateRtfForm
    success_url = './view#tab=0'

    def get_context_data(self, **kwargs):
        ctx = super(GenerateRtfFormView, self).get_context_data(**kwargs)
        ctx['object'] = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        ctx['service_id'] = self.service.id
        if self.request.GET.get('event-id'):
            date = self.request.GET.get('date')
            date = datetime.strptime(date, '%Y-%m-%d').date()
            appointment = Appointment()
            event = EventWithAct.objects.get(id=self.request.GET.get('event-id'))
            event = event.today_occurrence(date)
            appointment.init_from_event(event, self.service)
            ctx['event'] = event
            ctx['appointment'] = appointment
        return ctx

    def form_valid(self, form, **kwargs):
        ctx = self.get_context_data(**kwargs)
        patient = ctx['object']
        appointment = ctx['appointment']
        event = ctx['event']
        template_filename = form.cleaned_data.get('template_filename')
        dest_filename = datetime.now().strftime('%Y-%m-%d--%H:%M:%S') + '--' + template_filename
        from_path = os.path.join(settings.RTF_TEMPLATES_DIRECTORY, template_filename)
        to_path = ''
        persistent = True
        if settings.USE_PATIENT_FILE_RTF_REPOSITORY_DIRECTORY \
                or settings.RTF_REPOSITORY_DIRECTORY:
            if settings.USE_PATIENT_FILE_RTF_REPOSITORY_DIRECTORY:
                to_path = patient.get_ondisk_directory(self.service.name)
            if settings.RTF_REPOSITORY_DIRECTORY:
                to_path = os.path.join(to_path,
                    settings.RTF_REPOSITORY_DIRECTORY)
            to_path = os.path.join(to_path, dest_filename)
        else:
            # else : use temporary files
            persistent = False
            to_path = dest_filename
        variables = {'AD11': '', 'AD12': '', 'AD13': '', 'AD14': '',
            'AD15': '', 'AD18': '',
            'JOU1': formats.date_format(datetime.today(), "DATE_FORMAT"),
            'VIL1': u'Saint-Étienne',
            'RDV1': '', 'HEU1': '', 'THE1': '', 'DPA1': '',
            'NOM1': '', 'PRE1': '', 'NAI1': '', 'NUM2': '',
            'NOM2': '', 'PRE2': '', 'TPA1': '', 'NSS1': '',
            'TR01': '', 'TR02': '', 'TR03': '', 'TR04': '', 'TR05': '',
            'AD16': '', 'AD17': '', 'AD19': '',
            'AD21': '', 'AD22': '', 'AD23': '', 'AD24': '', 'AD25': '',
            'AD26': '', 'AD27': '', 'AD28': '', 'AD29': '',
            'RDV2': '' ,
        }
        list_rdvs = []
        for act in Act.objects.last_acts(patient):
            state = act.get_state()
            if state and state.state_name in ('VALIDE', 'ACT_DOUBLE'):
                rdv = "\t- %s" % formats.date_format(act.date, "DATE_FORMAT")
                if act.time:
                    rdv += " à %s" % formats.date_format(act.time, "TIME_FORMAT")
                list_rdvs.append(rdv)
        variables['RDV2'] = '\par'.join(list_rdvs)
        if appointment:
            variables['RDV1'] = formats.date_format(appointment.date, "DATE_FORMAT")
            variables['HEU1'] = appointment.begin_hour
            variables['THE1'] = ' '.join([str(i) for i in appointment.workers])# ou DPA1?
            variables['DPA1'] = variables['THE1']
        if patient:
            variables['NOM1'] = patient.last_name
            variables['PRE1'] = patient.first_name
            if patient.birthdate :
                variables['NAI1'] = patient.birthdate.strftime('%d/%m/%Y')
            variables['NUM2'] = patient.paper_id
            if patient.policyholder:
                variables['NOM2'] = patient.policyholder.last_name
                variables['PRE2'] = patient.policyholder.first_name
                if patient.policyholder.health_center:
                    variables['TPA1'] = patient.policyholder.health_center.name
                if patient.policyholder.social_security_id:
                    key = str(patient.policyholder.get_control_key())
                    if len(key) == 1:
                        key = '0' + key
                    variables['NSS1'] = \
                        ' '.join([patient.policyholder.social_security_id,
                            key])
            if patient.transportcompany:
                variables['TR01'] = patient.transportcompany.name
                variables['TR02'] = patient.transportcompany.address
                variables['TR03'] = patient.transportcompany.address_complement
                variables['TR04'] = patient.transportcompany.zip_code
                variables['TR05'] = patient.transportcompany.city
        variables['AD18'] = form.cleaned_data.get('phone_address') or ''
        for i, line in enumerate(form.cleaned_data.get('address').splitlines()):
            variables['AD%d' % (11+i)] = line
            if i == 4:
                break

        filename = make_doc_from_template(from_path, to_path, variables,
            persistent)

        client_dir = patient.get_client_side_directory(self.service.name)
        event.convocation_sent = True
        event.save()
        if not client_dir:
            content = File(file(filename))
            response = HttpResponse(content,'text/rtf')
            response['Content-Length'] = content.size
            response['Content-Disposition'] = 'attachment; filename="%s"' \
                % dest_filename.encode('utf-8')
            return response
        else:
            class LocalFileHttpResponseRedirect(HttpResponseRedirect):
                allowed_schemes = ['file']
            client_filepath = os.path.join(client_dir, dest_filename)
            return LocalFileHttpResponseRedirect('file://' + client_filepath)

generate_rtf_form = GenerateRtfFormView.as_view()


class PatientRecordsQuotationsView(cbv.ListView):
    model = PatientRecord
    template_name = 'dossiers/quotations.html'

    def _get_search_result(self, paginate_patient_records):
        patient_records = []
        for patient_record in paginate_patient_records:
            current_state = patient_record.get_current_state() or patient_record.get_state()
            deficiencies = [getattr(patient_record, field) \
                            for field in self.model.DEFICIENCY_FIELDS]
            anap = any(deficiencies)
            mises = reduce(lambda m1, m2: m1+m2, [list(getattr(patient_record, field).all()) for field in self.model.MISES_FIELDS])
            next_rdv = get_next_rdv(patient_record)
            last_rdv = get_last_rdv(patient_record)

            if next_rdv:
                next_rdv_datetime = next_rdv.start_datetime
            else:
                next_rdv_datetime = None
            if last_rdv:
                last_rdv_datetime = last_rdv['start_datetime']
            else:
                last_rdv_datetime = None
            patient_records.append(
                    {
                        'object': patient_record,
                        'state': current_state,
                        'anap': anap,
                        'mises': mises,
                        'next_rdv_date': next_rdv_datetime,
                        'last_rdv_date': last_rdv_datetime
                        }
                    )
        return patient_records

    def get_queryset(self):
        form = forms.QuotationsForm(data=self.request.GET or None)
        qs = super(PatientRecordsQuotationsView, self).get_queryset()
        without_quotations = self.request.GET.get('without_quotations')
        without_anap_quotations = self.request.GET.get('without_anap_quotations')
        if without_quotations:
            for field in self.model.MISES_FIELDS:
                mise_field = {'%s__isnull' % field: True}
                qs = qs.filter(**mise_field)

        if without_anap_quotations:
            for field in self.model.DEFICIENCY_FIELDS:
                anap_field = {field: 0}
                qs = qs.filter(**anap_field)

        states = self.request.GET.getlist('states')
        qs = qs.filter(last_state__status__id__in=states)

        try:
            date_actes_start = datetime.strptime(form.data['date_actes_start'], "%d/%m/%Y")
            qs = qs.filter(act__date__gte=date_actes_start.date()).distinct()
        except (ValueError, KeyError):
            pass
        try:
            date_actes_end = datetime.strptime(form.data['date_actes_end'], "%d/%m/%Y")
            qs = qs.filter(act__date__lte=date_actes_end.date()).distinct()
        except (ValueError, KeyError):
            pass
        qs = qs.filter(service=self.service).order_by('last_name').prefetch_related()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordsQuotationsView, self).get_context_data(**kwargs)
        ctx['search_form'] = forms.QuotationsForm(data=self.request.GET or None,
                service=self.service)
        patient_records = []
        page = self.request.GET.get('page')
        all = 'all' in self.request.GET
        if all:
            patient_records = ctx['object_list']
            ctx['all'] = all
            self.template_name = 'dossiers/quotations_print.html'
        else:
            paginator = Paginator(ctx['object_list'].filter(), 25)
            try:
                patient_records = paginator.page(page)
            except PageNotAnInteger:
                patient_records = paginator.page(1)
            except EmptyPage:
                patient_records = paginator.page(paginator.num_pages)
            ctx['paginate_patient_records'] = patient_records

        ctx['patient_records'] = self._get_search_result(patient_records)

        query = self.request.GET.copy()
        if 'page' in query:
            del query['page']
        ctx['query'] = query.urlencode()

        return ctx

patientrecord_quotations = PatientRecordsQuotationsView.as_view()

class NewProtectionStateView(cbv.CreateView):
    model = ProtectionState
    template_name = 'dossiers/generic_form.html'
    success_url = '../view#tab=1'
    form_class = forms.ProtectionStateForm

    def form_valid(self, form):
        self.patient = get_object_or_404(PatientRecord, id=self.kwargs.get('patientrecord_id',None))
        form.instance.patient = self.patient
        return super(NewProtectionStateView, self).form_valid(form)

new_protection = NewProtectionStateView.as_view()

class UpdateProtectionStateView(cbv.UpdateView):
    model = ProtectionState
    template_name = 'dossiers/generic_form.html'
    success_url = '../../view#tab=1'
    form_class = forms.ProtectionStateForm

    def form_valid(self, form):
        self.patient = get_object_or_404(PatientRecord, id=self.kwargs.get('patientrecord_id',None))
        form.instance.patient = self.patient
        return super(UpdateProtectionStateView, self).form_valid(form)

update_protection = UpdateProtectionStateView.as_view()

class DeleteProtectionStateView(cbv.DeleteView):
    model = ProtectionState
    template_name = 'dossiers/protection_confirm_delete.html'
    success_url = '../../view#tab=1'

delete_protection = DeleteProtectionStateView.as_view()

class PatientRecordsWaitingQueueView(cbv.ListView):
    model = PatientRecord
    template_name = 'dossiers/waiting_queue.html'

    def _get_search_result(self, paginate_patient_records,
            all_patient_records):
        patient_records = []
        if paginate_patient_records:
            position = 1
            for patient_record in paginate_patient_records:
                while patient_record.id != all_patient_records[position - 1].id:
                    position += 1
                patient_records.append(
                        {
                            'object': patient_record,
                            'position': position,
                            }
                        )
        return patient_records

    def get_queryset(self):
        form = forms.QuotationsForm(data=self.request.GET or None)
        qs = super(PatientRecordsWaitingQueueView, self).get_queryset()
        first_name = self.request.GET.get('first_name')
        last_name = self.request.GET.get('last_name')
        paper_id = self.request.GET.get('paper_id')
        id = self.request.GET.get('id')
        social_security_id = self.request.GET.get('social_security_id')
        qs = qs.filter(service=self.service,
            last_state__status__type='ACCUEIL')
        if last_name:
            qs = qs.filter(last_name__istartswith=last_name)
        if first_name:
            qs = qs.filter(first_name__istartswith=first_name)
        if paper_id:
            qs = qs.filter(paper_id__startswith=paper_id)
        if id:
            qs = qs.filter(id__startswith=id)
        if social_security_id:
            qs = qs.filter(models.Q(
                social_security_id__startswith=social_security_id)
                | models.Q(
                contacts__social_security_id__startswith=social_security_id))
        qs = qs.order_by('last_state__date_selected', 'created')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(PatientRecordsWaitingQueueView, self).get_context_data(**kwargs)
        ctx['search_form'] = forms.QuotationsForm(data=self.request.GET or None,
                service=self.service)
        patient_records = []
        page = self.request.GET.get('page')

        all = 'all' in self.request.GET
        if all:
            paginate_patient_records = ctx['object_list']
            ctx['all'] = all
            self.template_name = 'dossiers/waiting_queue_print.html'
        else:
            paginator = Paginator(ctx['object_list'].filter(), 25)
            try:
                paginate_patient_records = paginator.page(page)
            except PageNotAnInteger:
                paginate_patient_records = paginator.page(1)
            except EmptyPage:
                paginate_patient_records = paginator.page(paginator.num_pages)
            ctx['paginate_patient_records'] = paginate_patient_records

        all_patient_records = PatientRecord.objects.filter(
                service=self.service,
                last_state__status__type='ACCUEIL').order_by(
                'last_state__date_selected', 'created')
        ctx['patient_records'] = self._get_search_result(
            paginate_patient_records, all_patient_records)
        ctx['len_patient_records'] = all_patient_records.count()

        query = self.request.GET.copy()
        if 'page' in query:
            del query['page']
        ctx['query'] = query.urlencode()

        return ctx

patientrecord_waiting_queue = PatientRecordsWaitingQueueView.as_view()

class CreateDirectoryView(View, cbv.ServiceViewMixin):
    def post(self, request, *args, **kwargs):
        patient = PatientRecord.objects.get(id=kwargs['patientrecord_id'])
        service = Service.objects.get(slug=kwargs['service'])
        patient.get_ondisk_directory(service.name)
        messages.add_message(self.request, messages.INFO, u'Répertoire patient créé.')
        return HttpResponseRedirect('view')

create_directory = CreateDirectoryView.as_view()

class GenerateTransportPrescriptionFormView(cbv.FormView):
    template_name = 'dossiers/generate_transport_prescription_form.html'
    form_class = Form
    success_url = './view#tab=1'

    def get_context_data(self, **kwargs):
        ctx = super(GenerateTransportPrescriptionFormView, self).get_context_data(**kwargs)
        ctx['lieu'] = 'Saint-Etienne'
        ctx['date'] = formats.date_format(datetime.today(), "SHORT_DATE_FORMAT")
        ctx['id_etab'] = '''%s SAINT ETIENNE
66/68, RUE MARENGO
42000 SAINT ETIENNE''' % ctx['service'].upper()
        try:
            patient = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
            ctx['object'] = patient
            last_log = TransportPrescriptionLog.objects.filter(patient=patient).latest('created')
            if last_log:
                ctx['choices'] = last_log.get_choices()
                if 'lieu' in ctx['choices'] and ctx['choices']['lieu']:
                    ctx['lieu'] = ctx['choices']['lieu']
                if 'date' in ctx['choices'] and ctx['choices']['date']:
                    ctx['date'] = ctx['choices']['date']
                if 'id_etab' in ctx['choices'] and ctx['choices']['id_etab']:
                    ctx['id_etab'] = ctx['choices']['id_etab']
        except:
            pass
        return ctx

    def form_valid(self, form):
        patient = PatientRecord.objects.get(id=self.kwargs['patientrecord_id'])
        address = PatientAddress.objects.get(id=form.data['address_id'])
        path = render_transport(patient, address, form.data)
        content = File(file(path))
        log = TransportPrescriptionLog(patient=patient)
        log.set_choices(form.data)
        log.save()
        response = HttpResponse(content,'application/pdf')
        response['Content-Length'] = content.size
        dest_filename = "%s--prescription-transport-%s-%s.pdf" \
            % (datetime.now().strftime('%Y-%m-%d--%H:%M:%S'),
            patient.last_name.upper().encode('utf-8'),
            patient.first_name.encode('utf-8'))
        response['Content-Disposition'] = \
            'attachment; filename="%s"' % dest_filename
        return response

prescription_transport = GenerateTransportPrescriptionFormView.as_view()
