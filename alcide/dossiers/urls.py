from django.conf.urls import patterns, url

from alcide.cbv import ListView, CreateView, DeleteView, UpdateView

from models import PatientRecord
from forms import EditPatientRecordForm

urlpatterns = patterns('alcide.dossiers.views',
        url(r'^$', 'patientrecord_home'),
        url(r'^quotations$', 'patientrecord_quotations'),
        url(r'^waiting-queue$', 'patientrecord_waiting_queue'),
        url(r'^new$', 'new_patient_record'),
        url(r'^(?P<pk>\d+)/view$', 'patient_record'),
        url(r'^(?P<pk>\d+)/print$', 'patient_record_print', name='patientrecord_print'),
        url(r'^(?P<pk>\d+)/tab1$', 'tab1_general'),
        url(r'^(?P<pk>\d+)/tab2$', 'tab2_fiche_adm'),
        url(r'^(?P<pk>\d+)/tab3$', 'tab3_addresses'),
        url(r'^(?P<pk>\d+)/tab4$', 'tab4_notifs'),
        url(r'^(?P<pk>\d+)/tab5$', 'tab5_old_acts'),
        url(r'^(?P<pk>\d+)/tab6$', 'tab6_next_rdv'),
        url(r'^(?P<pk>\d+)/tab7$', 'tab7_socialisation'),
        url(r'^(?P<pk>\d+)/tab8$', 'tab8_medical'),
        url(r'^(?P<pk>\d+)/delete$', 'patientrecord_delete'),
        url(r'^(?P<pk>\d+)/update/paper_id$', 'update_paper_id'),
        url(r'^(?P<patientrecord_id>\d+)/update-state$', 'state_form'),
        url(r'^(?P<patientrecord_id>\d+)/address/new$', 'new_patient_address'),
        url(r'^(?P<patientrecord_id>\d+)/address/(?P<pk>\d+)/update$', 'update_patient_address'),
        url(r'^(?P<patientrecord_id>\d+)/address/(?P<pk>\d+)/del$', 'delete_patient_address'),
        url(r'^(?P<patientrecord_id>\d+)/contact/new$', 'new_patient_contact'),
        url(r'^(?P<patientrecord_id>\d+)/contact/(?P<pk>\d+)/update$', 'update_patient_contact'),
        url(r'^(?P<patientrecord_id>\d+)/contact/(?P<pk>\d+)/del$', 'delete_patient_contact'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_treatment/new$', 'new_healthcare_treatment'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_treatment/(?P<pk>\d+)/update$', 'update_healthcare_treatment'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_treatment/(?P<pk>\d+)/del$', 'delete_healthcare_treatment'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_diagnostic/new$', 'new_healthcare_diagnostic'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_diagnostic/(?P<pk>\d+)/update$', 'update_healthcare_diagnostic'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_diagnostic/(?P<pk>\d+)/del$', 'delete_healthcare_diagnostic'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_notification/new$', 'new_healthcare_notification'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_notification/(?P<pk>\d+)/update$', 'update_healthcare_notification'),
        url(r'^(?P<patientrecord_id>\d+)/healthcare_notification/(?P<pk>\d+)/del$', 'delete_healthcare_notification'),
        url(r'^(?P<patientrecord_id>\d+)/socialisation/new$', 'new_socialisation_duration'),
        url(r'^(?P<patientrecord_id>\d+)/socialisation/(?P<pk>\d+)/update$', 'update_socialisation_duration'),
        url(r'^(?P<patientrecord_id>\d+)/socialisation/(?P<pk>\d+)/del$', 'delete_socialisation_duration'),
        url(r'^(?P<patientrecord_id>\d+)/state/(?P<pk>\d+)/update$', 'update_patient_state'),
        url(r'^(?P<patientrecord_id>\d+)/state/(?P<pk>\d+)/del$', 'delete_patient_state'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_request/new$', 'new_mdph_request'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_request/(?P<pk>\d+)/update$', 'update_mdph_request'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_request/(?P<pk>\d+)/del$', 'delete_mdph_request'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_response/new$', 'new_mdph_response'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_response/(?P<pk>\d+)/update$', 'update_mdph_response'),
        url(r'^(?P<patientrecord_id>\d+)/mdph_response/(?P<pk>\d+)/del$', 'delete_mdph_response'),
        url(r'^(?P<patientrecord_id>\d+)/generate$', 'generate_rtf_form'),
        url(r'^(?P<patientrecord_id>\d+)/create-directory$', 'create_directory', name="create_directory"),
        url(r'^(?P<patientrecord_id>\d+)/prescription-transport$', 'prescription_transport'),
        url(r'^(?P<patientrecord_id>\d+)/protection/new$', 'new_protection'),
        url(r'^(?P<patientrecord_id>\d+)/protection/(?P<pk>\d+)/update$', 'update_protection'),
        url(r'^(?P<patientrecord_id>\d+)/protection/(?P<pk>\d+)/del$', 'delete_protection'),)
