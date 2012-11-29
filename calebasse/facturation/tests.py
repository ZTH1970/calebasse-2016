# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil import rrule

from django.test import TestCase
from django.contrib.auth.models import User

from calebasse.actes.validation import automated_validation, \
    are_all_acts_of_the_day_locked, \
    get_days_with_acts_not_locked
from calebasse.actes.models import EventAct
from calebasse.dossiers.models import create_patient, PatientRecord, \
    SessadHealthCareNotification, CmppHealthCareTreatment, CmppHealthCareDiagnostic
from calebasse.dossiers.models import Status
from calebasse.ressources.models import ActType, Service, WorkerType
from calebasse.personnes.models import Worker

from list_acts import list_acts_for_billing_CAMSP, \
    list_acts_for_billing_SESSAD, list_acts_for_billing_CMPP


class FacturationTest(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='John')

        self.wtype = WorkerType.objects.create(name='ElDoctor', intervene=True)
        self.therapist1 = Worker.objects.create(first_name='Bob', last_name='Leponge', type=self.wtype)
        self.therapist2 = Worker.objects.create(first_name='Jean', last_name='Valjean', type=self.wtype)
        self.therapist3 = Worker.objects.create(first_name='Pierre', last_name='PaulJacques', type=self.wtype)
        self.act_type = ActType.objects.create(name='trepanation')

    def test_facturation_camsp(self):
        service_camsp = Service.objects.get(name='CAMSP')

        patient_a = create_patient('a', 'A', service_camsp, self.creator, date_selected=datetime(2020, 10, 5))
        act0 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 6, 10, 15),
                end_datetime=datetime(2020, 10, 6, 12, 20))
        status_suivi = Status.objects.filter(services__name='CAMSP').filter(type='SUIVI')[0]
        patient_a.set_state(status_suivi, self.creator, date_selected=datetime(2020, 10, 7))
        act1 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 10, 15),
                end_datetime=datetime(2020, 10, 7, 12, 20))
        act2 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 14, 15),
                end_datetime=datetime(2020, 10, 7, 16, 20))
        act3 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 16, 20),
                end_datetime=datetime(2020, 10, 7, 17, 20))
        status_clos = Status.objects.filter(services__name='CAMSP').filter(type='CLOS')[0]
        patient_a.set_state(status_clos, self.creator, date_selected=datetime(2020, 10, 8))
        act4 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 8, 10, 15),
                end_datetime=datetime(2020, 10, 8, 12, 20))

        patient_b = create_patient('b', 'B', service_camsp, self.creator, date_selected=datetime(2020, 10, 4))
        act5 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 4, 10, 15),
                end_datetime=datetime(2020, 10, 4, 12, 20))
        act6 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 5, 10, 15),
                end_datetime=datetime(2020, 10, 5, 12, 20))
        act6.set_state('ABS_EXC', self.creator)
        act7 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 5, 10, 15),
                end_datetime=datetime(2020, 10, 5, 12, 20))
        act7.switch_billable = True
        act7.save()
        patient_b.set_state(status_suivi, self.creator, date_selected=datetime(2020, 10, 6))
        act8 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 10, 15),
                end_datetime=datetime(2020, 10, 7, 12, 20))
        act9 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 14, 15),
                end_datetime=datetime(2020, 10, 7, 16, 20))
        act10 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 7, 16, 20),
                end_datetime=datetime(2020, 10, 7, 17, 20))
        act11 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_b, [self.therapist3],
                self.act_type, service_camsp, start_datetime=datetime(2020, 10, 8, 10, 15),
                end_datetime=datetime(2020, 10, 8, 12, 20))
        patient_b.set_state(status_clos, self.creator, date_selected=datetime(2020, 10, 9))

        automated_validation(datetime(2020, 10, 5), service_camsp, self.creator)
        automated_validation(datetime(2020, 10, 6), service_camsp, self.creator)
        automated_validation(datetime(2020, 10, 7), service_camsp, self.creator)
        automated_validation(datetime(2020, 10, 8), service_camsp, self.creator)

        not_locked, days_not_locked, not_valide, not_billable, rejected, selected = \
            list_acts_for_billing_CAMSP(datetime(2020, 10, 4), datetime(2020, 10, 8), service_camsp)

        self.assertEqual(len(days_not_locked), 1)

        self.assertTrue(act1 in selected[patient_a])
        self.assertTrue(act2 in selected[patient_a])
        self.assertTrue(act3 in selected[patient_a])
        acts_rejected = [x[0] for x in rejected[patient_a]]
        self.assertTrue(act0 in acts_rejected)
        self.assertTrue(act4 in acts_rejected)

        acts_not_locked = [x[0] for x in not_locked[patient_b]]
        self.assertTrue(act5 in acts_not_locked)
        acts_not_valide = [x[0] for x in not_valide[patient_b]]
        self.assertTrue(act6 in acts_not_valide)
        self.assertTrue(act7 in not_billable[patient_b])
        self.assertTrue(act8 in selected[patient_b])
        self.assertTrue(act9 in selected[patient_b])
        self.assertTrue(act10 in selected[patient_b])
        self.assertTrue(act11 in selected[patient_b])

        states = patient_b.get_states_history()
        patient_b.change_day_selected_of_state(states[2], datetime(2020, 10, 7))
        not_locked, days_not_locked, not_valide, not_billable, rejected, selected = \
            list_acts_for_billing_CAMSP(datetime(2020, 10, 4), datetime(2020, 10, 8), service_camsp)
        acts_not_locked = [x[0] for x in not_locked[patient_b]]
        self.assertTrue(act5 in acts_not_locked)
        acts_not_valide = [x[0] for x in not_valide[patient_b]]
        self.assertTrue(act6 in acts_not_valide)
        self.assertTrue(act7 in not_billable[patient_b])
        acts_rejected = [x[0] for x in rejected[patient_b]]
        self.assertTrue(act8 in acts_rejected)
        self.assertTrue(act9 in acts_rejected)
        self.assertTrue(act10 in acts_rejected)
        self.assertTrue(act11 in acts_rejected)

        states = patient_b.get_states_history()
        patient_b.change_day_selected_of_state(states[2], datetime(2020, 10, 9))
        patient_b.change_day_selected_of_state(states[1], datetime(2020, 10, 8))
        not_locked, days_not_locked, not_valide, not_billable, rejected, selected = \
            list_acts_for_billing_CAMSP(datetime(2020, 10, 4), datetime(2020, 10, 8), service_camsp)
        acts_not_locked = [x[0] for x in not_locked[patient_b]]
        self.assertTrue(act5 in acts_not_locked)
        acts_not_valide = [x[0] for x in not_valide[patient_b]]
        self.assertTrue(act6 in acts_not_valide)
        self.assertTrue(act7 in not_billable[patient_b])
        acts_rejected = [x[0] for x in rejected[patient_b]]
        self.assertTrue(act8 in acts_rejected)
        self.assertTrue(act9 in acts_rejected)
        self.assertTrue(act10 in acts_rejected)
        self.assertTrue(act11 in selected[patient_b])

    def test_facturation_sessad(self):
        service_sessad = Service.objects.get(name='SESSAD DYS')

        patient_a = create_patient('a', 'A', service_sessad, self.creator, date_selected=datetime(2020, 10, 5))
        act0 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_sessad, start_datetime=datetime(2020, 10, 6, 10, 15),
                end_datetime=datetime(2020, 10, 6, 12, 20))
        status_traitement = Status.objects.filter(services__name='SESSAD DYS').filter(type='TRAITEMENT')[0]
        patient_a.set_state(status_traitement, self.creator, date_selected=datetime(2020, 10, 7))
        act1 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_sessad, start_datetime=datetime(2020, 10, 7, 10, 15),
                end_datetime=datetime(2020, 10, 7, 12, 20))
        act2 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_sessad, start_datetime=datetime(2020, 10, 7, 14, 15),
                end_datetime=datetime(2020, 10, 7, 16, 20))
        act3 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_sessad, start_datetime=datetime(2020, 10, 7, 16, 20),
                end_datetime=datetime(2020, 10, 7, 17, 20))
        status_clos = Status.objects.filter(services__name='SESSAD DYS').filter(type='CLOS')[0]
        patient_a.set_state(status_clos, self.creator, date_selected=datetime(2020, 10, 8))
        act4 = EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_sessad, start_datetime=datetime(2020, 10, 8, 10, 15),
                end_datetime=datetime(2020, 10, 8, 12, 20))

        automated_validation(datetime(2020, 10, 6), service_sessad, self.creator)
        automated_validation(datetime(2020, 10, 7), service_sessad, self.creator)
        automated_validation(datetime(2020, 10, 8), service_sessad, self.creator)

        not_locked, days_not_locked, not_valide, not_billable, rejected, missing_valid_notification, selected = \
            list_acts_for_billing_SESSAD(datetime(2020, 10, 4), datetime(2020, 10, 8), service_sessad)
        self.assertEqual(not_locked, {})
        self.assertEqual(not_valide, {})
        self.assertEqual(not_billable, {})
        self.assertEqual(len(rejected[patient_a]), 2)
        self.assertEqual(len(missing_valid_notification[patient_a]), 3)
        self.assertEqual(selected, {})

        SessadHealthCareNotification(patient=patient_a, author=self.creator, start_date=datetime(2020,10,7), end_date=datetime(2021,10,6)).save()
        not_locked, days_not_locked, not_valide, not_billable, rejected, missing_valid_notification, selected = \
            list_acts_for_billing_SESSAD(datetime(2020, 10, 4), datetime(2020, 10, 8), service_sessad)
        self.assertEqual(not_locked, {})
        self.assertEqual(not_valide, {})
        self.assertEqual(not_billable, {})
        self.assertEqual(len(rejected[patient_a]), 2)
        self.assertEqual(missing_valid_notification, {})
        self.assertEqual(len(selected[patient_a]), 3)

    def test_facturation_cmpp(self):
        service_cmpp = Service.objects.get(name='CMPP')

        patient_a = create_patient('a', 'A', service_cmpp, self.creator, date_selected=datetime(2020, 10, 1))
        acts = [ EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_cmpp, start_datetime=datetime(2020, 10, i, 10, 15),
                end_datetime=datetime(2020, 10, i, 12, 20)) for i in range (1, 32)]
        status_accueil = Status.objects.filter(services__name='CMPP').filter(type='ACCUEIL')[0]
        status_diagnostic = Status.objects.filter(services__name='CMPP').filter(type='DIAGNOSTIC')[0]
        status_traitement = Status.objects.filter(services__name='CMPP').filter(type='TRAITEMENT')[0]

        self.assertEqual(patient_a.get_state().status, status_accueil)
        automated_validation(datetime(2020, 10, 1), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 2), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 3), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 4), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 5), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 6), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_diagnostic)
        automated_validation(datetime(2020, 10, 7), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_traitement)
        automated_validation(datetime(2020, 10, 8), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_traitement)
        automated_validation(datetime(2020, 10, 9), service_cmpp, self.creator)
        patient_a = PatientRecord.objects.get(id=patient_a.id)
        self.assertEqual(patient_a.get_state().status, status_traitement)
        for i in range(10, 32):
            automated_validation(datetime(2020, 10, i), service_cmpp, self.creator)
            patient_a = PatientRecord.objects.get(id=patient_a.id)
            self.assertEqual(patient_a.get_state().status, status_traitement)

        acts_2 = [ EventAct.objects.create_patient_appointment(self.creator, 'RDV', patient_a, [self.therapist3],
                self.act_type, service_cmpp, start_datetime=datetime(2020, 11, i, 10, 15),
                end_datetime=datetime(2020, 11, i, 12, 20)) for i in range (1, 31)]
        for i in range(1, 31):
            automated_validation(datetime(2020, 11, i), service_cmpp, self.creator)
            patient_a = PatientRecord.objects.get(id=patient_a.id)
            self.assertEqual(patient_a.get_state().status, status_traitement)

        self.assertEqual(get_days_with_acts_not_locked(datetime(2020, 10, 1), datetime(2020, 11, 30)), [])

        acts = acts + acts_2

        hct = CmppHealthCareTreatment(patient=patient_a, start_date=datetime(2020, 10, 7), author=self.creator)
        hct.save()
        hct.add_prolongation()
        billing_cmpp = list_acts_for_billing_CMPP(datetime(2020, 11, 30), service_cmpp)
        self.assertEqual(len(billing_cmpp[4][patient_a]), 6)
        self.assertEqual(len(billing_cmpp[5][patient_a]), 40)
        self.assertEqual(len(billing_cmpp[6][patient_a]), 15)

    def test_prices(self):
        pass
