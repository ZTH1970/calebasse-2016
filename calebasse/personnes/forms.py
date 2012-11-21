# -*- coding: utf-8 -*-
from django import forms
from django.forms.models import (inlineformset_factory, modelformset_factory,
        BaseInlineFormSet, BaseModelFormSet)
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from calebasse.ressources.models import WorkerType, Service

from models import Worker, UserWorker, TimeTable, Holiday


class UserForm(forms.ModelForm):
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'password_mismatch': _("The two password fields didn't match."),
    }

    worker = forms.ModelChoiceField(label=_('Personnel'),
            queryset=Worker.objects.all(), empty_label=_('None'),
            required=False)
    password1 = forms.CharField(label=_("Password"),
        widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."),
        required=False)

    def __init__(self, service=None, *args, **kwargs):
        self.service = service
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['worker'].queryset = Worker.objects.for_service(service)
        self.fields['username'].label = _('Identifiant')
        if self.instance:
            try:
                worker = self.instance.userworker.worker
                self.fields['worker'].initial = worker.pk
            except UserWorker.DoesNotExist:
                pass

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        if self.instance is None:
            try:
                User.objects.get(username=username)
                raise forms.ValidationError(self.error_messages['duplicate_username'])
            except User.DoesNotExist:
                pass
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'])
        return password2

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'worker')

    def save(self, commit=True):
        import pdb
        pdb.set_trace()
        instance = super(UserForm, self).save(commit=False)
        if self.cleaned_data['password1']:
            instance.set_password(self.cleaned_data['password1'])
        worker = self.cleaned_data.get('worker')
        if worker is not None:
            self.first_name = worker.first_name
            self.last_name = worker.last_name
            def save_m2m():
                if UserWorker.objects.filter(user_ptr=self.instance):
                    userworker = self.instance.userworker
                    userworker.worker = worker
                    userworker.save()
                else:
                    UserWorker.objects.create(id=self.instance.id, worker=worker)
            self.save_m2m = save_m2m
        else:
            self.save_m2m = lambda: None
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class WorkerSearchForm(forms.Form):
    last_name = forms.CharField(label=u'Nom', required=False)
    first_name = forms.CharField(label=u'Prénom', required=False)
    profession = forms.ModelChoiceField(label=u'Profession',
            queryset=WorkerType.objects.all(), required=False)

    INTERVENE_STATUS_CHOICES = {
            'a': u'Thérapeute',
            'b': u'Non-thérapeute'
    }

    intervene_status = forms.MultipleChoiceField(
        choices=INTERVENE_STATUS_CHOICES.iteritems(),
        widget=forms.CheckboxSelectMultiple,
        initial=INTERVENE_STATUS_CHOICES.keys(),
        required=False)

class WorkerIdForm(forms.ModelForm):
    sex = forms.CharField(label='Genre')

    class Meta:
        model = Worker
        fields = ('last_name', 'first_name', 'sex')

class WorkerServiceForm(forms.ModelForm):
    class Meta:
        model = Worker
        fields = ('services',)
        widgets = {
                'services': forms.CheckboxSelectMultiple,
        }


class BaseTimetableFormSet(BaseInlineFormSet):
    def __init__(self, weekday=None, *args, **kwargs):
        kwargs['queryset'] = kwargs.get('queryset', TimeTable.objects).filter(weekday=weekday)
        kwargs['initial'] = [{ 'services': Service.objects.all().values_list('pk', flat=True) }] * 3
        super(BaseTimetableFormSet, self).__init__(*args, **kwargs)


class BaseTimeTableForm(forms.ModelForm):
    class Meta:
        model = TimeTable
        widgets = {
                'services': forms.CheckboxSelectMultiple,
        }

TimetableFormSet = inlineformset_factory(Worker, TimeTable,
        formset=BaseTimetableFormSet,
        form=BaseTimeTableForm,
        fields=('start_time', 'end_time', 'start_date', 'end_date', 'services'))

HolidayFormSet = inlineformset_factory(
        Worker, Holiday,
        fields=('start_date', 'end_date', 'start_time', 'end_time'))

class HolidaySearchForm(forms.Form):
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)

    def clean(self):
        cleaned_data = super(HolidaySearchForm, self).clean()
        if cleaned_data.get('start_date') or cleaned_data.get('end_date'):
            if not cleaned_data.get('start_date') \
                   or not cleaned_data.get('end_date'):
                raise forms.ValidationError(u'Vous devez fournir une date de début et de fin')
            if cleaned_data['start_date'] > cleaned_data['end_date']:
                raise forms.ValidationError(u'La date de début doit être supérieure à la date de fin')
        return cleaned_data

class YearlyHolidayBaseFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        old_form = self.form
        self.form = lambda *args, **kwargs: old_form(*args, service=self.service, **kwargs)
        super(YearlyHolidayBaseFormSet, self).__init__(*args, **kwargs)

class YearlyHolidayForm(forms.ModelForm):
    for_all_services = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        super(YearlyHolidayForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.id:
            self.initial['for_all_services'] = self.instance.service is None


    def save(self, commit=True):
        instance = super(YearlyHolidayForm, self).save(commit=False)
        if not self.cleaned_data.get('for_all_services', False):
            instance.service = self.service
        if commit:
            instance.save()
        return instance

    class Meta:
        form = Holiday

YearlyHolidayFormSet = modelformset_factory(Holiday,
        can_delete=True,
        form=YearlyHolidayForm,
        formset=YearlyHolidayBaseFormSet,
        fields=('start_date', 'end_date'))
