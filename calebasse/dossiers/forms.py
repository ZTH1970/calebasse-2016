# -*- coding: utf-8 -*-

from datetime import date

from django import forms
from django.forms import ModelForm, Form

from calebasse.dossiers.models import (PatientRecord,
    PatientAddress, PatientContact, DEFAULT_ACT_NUMBER_TREATMENT,
    CmppHealthCareTreatment)
from calebasse.dossiers.states import STATE_CHOICES

from ajax_select import make_ajax_field


class EditPatientRecordForm(ModelForm):
    class Meta:
        model = PatientRecord

class SearchForm(Form):
    last_name = forms.CharField(label=u'Nom', required=False)
    first_name = forms.CharField(label=u'Prénom', required=False)
    folder_id = forms.CharField(label=u'Numéro de dossier', required=False)
    social_security_id = forms.CharField(label=u"Numéro d'assuré social", required=False)
    states = forms.MultipleChoiceField(
            widget=forms.CheckboxSelectMultiple(attrs={'class':'checkbox_state'}),
            choices=STATE_CHOICES, initial=(0,1,2,3,4))

class StateForm(Form):
    patient_id = forms.IntegerField()
    service_id = forms.IntegerField()
    state_type = forms.CharField(max_length=40)
    date = forms.DateField(label=u'Date')
    comment = forms.CharField(label='Commentaire',
            required=False, widget=forms.Textarea)

class NewPatientRecordForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('last_name', 'first_name')

class GeneralForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('comment', 'pause')
        widgets = {
                'comment': forms.Textarea(attrs={'cols': 50, 'rows': 5}),
                }

class CivilStatusForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('first_name', 'last_name', 'birthdate', 'gender', 'nationality')

class PhysiologyForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('size', 'weight', 'pregnancy_term')

class InscriptionForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('analysemotive', 'familymotive', 'advicegiver')
        widgets = {}

class FamilyForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('sibship_place', 'nb_children_family', 'parental_authority',
                'family_situation', 'child_custody')

class TransportFrom(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('transporttype', 'transportcompany')

class PaperIDForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('paper_id', )

class PolicyHolderForm(ModelForm):
    class Meta:
        model = PatientRecord
        fields = ('policyholder', )
        widgets = { 'policyholder': forms.RadioSelect() }

class FollowUpForm(ModelForm):
    coordinators = make_ajax_field(PatientRecord, 'coordinators', 'worker', True)
    class Meta:
        model = PatientRecord
        fields = ('coordinators', 'externaldoctor', 'externalintervener')

class PatientContactForm(ModelForm):
    addresses = make_ajax_field(PatientContact, 'addresses', 'addresses', True)
    class Meta:
        model = PatientContact
        widgets = {
                'contact_comment': forms.Textarea(attrs={'cols': 50, 'rows': 2}),
                'key': forms.TextInput(attrs={'size': 4}),
                'twinning_rank': forms.TextInput(attrs={'size': 4}),
                'large_regime': forms.Select(attrs={'class': 'small_select'}),
                'healt_fund': forms.Select(attrs={'class': 'small_select'}),
                'healt_center': forms.Select(attrs={'class': 'small_select'}),
                }

class PatientAddressForm(ModelForm):

    class Meta:
        model = PatientAddress
        widgets = {
                'comment': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
                'zip_code': forms.TextInput(attrs={'size': 10}),
                'number': forms.TextInput(attrs={'size': 10}),
                }

class CmppHealthCareTreatmentForm(ModelForm):
    class Meta:
        model = CmppHealthCareTreatment
        fields = ('start_date', 'end_date', '_act_number',
                'prolongation', 'comment', 'patient', 'author')
        widgets = {
                'comment': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
                'patient': forms.HiddenInput(),
                'author': forms.HiddenInput(),
                }
#    start_date = forms.DateField(label=u'Date de début')
#    patient_id = forms.IntegerField()
#    act_number = forms.IntegerField(label=u"Nombre d'actes couverts", initial=DEFAULT_ACT_NUMBER_TREATMENT)
#    comment = forms.CharField(label=u"Commentaire",
#            required=False, widget=forms.Textarea)
