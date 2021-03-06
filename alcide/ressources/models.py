# -*- coding: utf-8 -*-

from datetime import date, datetime
import bisect

from django.db import models
from django.db.models import query
from model_utils import Choices

from alcide.models import PhoneNumberField, ZipCodeField

from model_utils.managers import PassThroughManager


class ServiceLinkedQuerySet(query.QuerySet):
    def for_service(self, service, allow_global=True):
        '''Allows service local and service global objects'''
        return self.filter(models.Q(service=service)
                |models.Q(service__isnull=allow_global))

ServiceLinkedManager = PassThroughManager.for_queryset_class(ServiceLinkedQuerySet)

class NamedAbstractModel(models.Model):
    name = models.CharField(max_length=150, verbose_name=u'Nom')

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, unicode(self))

    class Meta:
        abstract = True
        ordering = ['name']

class ServiceLinkedAbstractModel(models.Model):
    objects = ServiceLinkedManager()
    service = models.ForeignKey('Service', null=True, blank=True)

    class Meta:
        abstract = True

DEST_TYPE = {
    # code grand regime: type destinataire
    '01': 'CT', # regime general
    '02': 'MA', # agricole
    '03': 'SR', # independant
    '04': 'CF', # sncf
    '05': 'RP', # ratp
    '06': 'EN', # invalide marine
    '07': 'RM', # minier
    '08': 'CM', # militaire
    '10': 'CE', # notaires
    '12': 'CI', # cci paris
    '14': 'AN', # assemblee nationale
    '15': 'SE', # senat
    '16': 'PB', # port autonome bordeaux
    '90': 'CC', # cultes
    '91': 'SM', # ensuite toutes les mutuelles nationales
    '92': 'SM',
    '93': 'SM',
    '94': 'SM',
    '95': 'SM',
    '96': 'SM',
    '99': 'SM',
}


class HealthCenter(NamedAbstractModel):
    class Meta:
        verbose_name = u'Centre d\'assurance maladie'
        verbose_name_plural = u'Centres d\'assurances maladie'

    def __unicode__(self):
        return self.large_regime.code + ' ' + self.health_fund + ' ' + self.code + ' ' + self.name

    code = models.CharField(verbose_name=u"Code du centre",
            max_length=4,
            null=True, blank=True)
    large_regime = models.ForeignKey('LargeRegime',
            verbose_name=u"Grand régime")
    dest_organism = models.CharField(max_length=8,
            verbose_name=u"Organisme destinataire")
    computer_center_code = models.CharField(max_length=8,
            verbose_name=u"Code centre informatique",
            null=True, default=True)
    abbreviation = models.CharField(verbose_name=u'Abbrévation',
            max_length=8,
            null=True, default=True)
    health_fund = models.CharField(verbose_name=u"Numéro de la caisse",
            max_length=3)
    active = models.BooleanField(default=True, verbose_name=u"Active")
    address = models.CharField(max_length=120, verbose_name=u"Adresse")
    address_complement = models.CharField(max_length=120, blank=True,
            null=True, default=None, verbose_name=u"Adresse complémentaire")
    zip_code = models.CharField(max_length=8, verbose_name=u"Code postal")
    city = models.CharField(max_length=80, verbose_name=u"Ville")
    phone = models.CharField(max_length=30, verbose_name=u"Téléphone")
    fax = models.CharField(max_length=30,
            null=True, blank=True, verbose_name=u"Fax")
    email = models.EmailField(
            null=True, blank=True, verbose_name=u"Courriel")
    accounting_number = models.CharField(max_length=30,
             null=True, blank=True, verbose_name=u"Numéro de compte")
    correspondant = models.CharField(max_length=80, verbose_name=u"Correspondant")
    hc_invoice = models.ForeignKey('HealthCenter',
            verbose_name=u"Centre pour facturation (optionnel)",
            null=True, blank=True, default=None)

    def b2_000(self):
        '''
        renvoie le numéro destinataire selon la norme B2, type 000
        '''
        return DEST_TYPE[self.large_regime.code] + '000000' + self.large_regime.code[0:2] + self.computer_center_code[0:3] + self.dest_organism[0:3]


class LargeRegime(NamedAbstractModel):
    class Meta:
        verbose_name = u'Grand régime'
        verbose_name_plural = u'Grands régimes'

    def __unicode__(self):
        return self.code + ' ' + self.name

    code = models.CharField(verbose_name=u"Code grand régime",
            max_length=2)


class TransportCompany(NamedAbstractModel):
    description = models.TextField(blank=True, null=True, default=None)
    address = models.CharField(max_length=120,
            verbose_name=u"Adresse", blank=True, null=True, default=None)
    address_complement = models.CharField(max_length=120,
            blank=True,
            null=True,
            default=None,
            verbose_name=u"Complément d'adresse")
    zip_code = ZipCodeField(verbose_name=u"Code postal",
        blank=True, null=True, default=None)
    city = models.CharField(max_length=80, verbose_name=u"Ville",
        blank=True, null=True, default=None)
    phone = PhoneNumberField(verbose_name=u"Téléphone",
        blank=True, null=True, default=None)
    fax = models.CharField(max_length=30,
            blank=True, null=True, default=None)
    email = models.EmailField(blank=True, null=True)
    correspondant = models.CharField(max_length=80, blank=True, null=True)
    old_camsp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CAMSP', blank=True, null=True)
    old_cmpp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CMPP', blank=True, null=True)
    old_sessad_dys_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD TED', blank=True, null=True)
    old_sessad_ted_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD DYS', blank=True, null=True)

    class Meta:
        verbose_name = u'Compagnie de transport'
        verbose_name_plural = u'Compagnies de transport'


class ManagementCode(NamedAbstractModel):
    class Meta:
        verbose_name = u'Code de gestion'
        verbose_name_plural = u'Codes de gestion'

    def __unicode__(self):
        return self.code + ' ' + self.name

    code = models.CharField(verbose_name=u"Code",
            max_length=10)
    old_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID', blank=True, null=True)


class UninvoicableCode(NamedAbstractModel):
    class Meta:
        verbose_name = u'Code de non-facturation'
        verbose_name_plural = u'Codes de non-facturation'


class Office(NamedAbstractModel):
    class Meta:
        verbose_name = u'Établissement'
        verbose_name_plural = u'Établissements'

    def __unicode__(self):
        return self.name

    description = models.TextField(blank=True, null=True)

    # Contact
    phone = PhoneNumberField(verbose_name=u"Téléphone", blank=True, null=True)
    fax = PhoneNumberField(verbose_name=u"Fax", blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Address
    address = models.CharField(max_length=120,
            verbose_name=u"Adresse", blank=True, null=True, default=None)
    address_complement = models.CharField(max_length=120,
            blank=True,
            null=True,
            default=None,
            verbose_name=u"Complément d'adresse")
    zip_code = ZipCodeField(verbose_name=u"Code postal",
            blank=True, null=True, default=None)
    city = models.CharField(max_length=80, verbose_name=u"Ville",
            blank=True, null=True, default=None)

    # TODO: add this fields : finess, suite, dm, dpa, genre, categorie, statut_juridique, mft, mt, dmt

class SchoolType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type du lieu de socialisation'
        verbose_name_plural = u'Types du lieu de socialisation'

    services = models.ManyToManyField('ressources.Service')

class School(NamedAbstractModel):
    class Meta:
        verbose_name = u'Lieu de socialisation'
        verbose_name_plural = u'Lieux de socialisation'

    def __unicode__(self):
        if self.school_type.name != 'Inconnu':
            return unicode(self.school_type) + ' ' + self.name
        return self.name

    def save(self, **kwargs):
        self.display_name = ""
        if self.school_type.name != 'Inconnu':
            self.display_name = unicode(self.school_type) + ' ' + self.name
        else:
            self.display_name = self.name
        if self.address:
            self.display_name += u" - "  + self.address
        if self.zip_code:
            self.display_name += u" "  + self.zip_code
        if self.city:
            self.display_name += u" "  + self.city
        if self.private:
            self.display_name += u" (Privé)"
        else:
            self.display_name += u" (Public)"
        super(School, self).save(**kwargs)

    display_name = models.CharField(max_length=256,
            blank=True, null=True, default='')
    school_type = models.ForeignKey('ressources.SchoolType',
        verbose_name=u"Type d'établissement")
    description = models.TextField(blank=True, null=True, default=None)
    address = models.CharField(max_length=120,
            verbose_name=u"Adresse", blank=True, null=True, default=None)
    address_complement = models.CharField(max_length=120,
            blank=True,
            null=True,
            default=None,
            verbose_name=u"Complément d'adresse")
    zip_code = ZipCodeField(verbose_name=u"Code postal",
        blank=True, null=True, default=None)
    city = models.CharField(max_length=80, verbose_name=u"Ville",
        blank=True, null=True, default=None)
    phone = PhoneNumberField(verbose_name=u"Téléphone",
        blank=True, null=True, default=None)
    fax = models.CharField(max_length=30,
            blank=True, null=True, default=None)
    email = models.EmailField(blank=True, null=True, default=None)
    director_name = models.CharField(max_length=70,
            blank=True, null=True, default=None,
            verbose_name=u"Nom du directeur")
    old_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID', blank=True, null=True)
    old_service = models.CharField(max_length=256,
            verbose_name=u'Ancien Service', blank=True, null=True)
    private = models.BooleanField(verbose_name=u"Privé", default=False)
    services = models.ManyToManyField('ressources.Service', blank=True, null=True)


class SchoolTeacherRole(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type de rôle des professeurs'
        verbose_name_plural = u'Types de rôle des professeurs'


class SchoolLevel(NamedAbstractModel):
    old_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID', blank=True, null=True)
    old_service = models.CharField(max_length=256,
            verbose_name=u'Ancien Service', blank=True, null=True)

    class Meta:
        verbose_name = u'Classe'
        verbose_name_plural = u'Classes'


class SocialisationDuration(models.Model):
    class Meta:
        verbose_name = u'Période de socialisation'
        verbose_name_plural = u'Périodes de socialisation'

    school = models.ForeignKey('ressources.School',
        verbose_name=u'Lieu de socialisation',
        blank=True, null=True,
        on_delete=models.SET_NULL)
    level = models.ForeignKey('ressources.SchoolLevel',
        verbose_name=u'Classe',
        blank=True, null=True,
        on_delete=models.SET_NULL)
    redoublement = models.BooleanField(verbose_name=u"Redoublement",
            default=False)
    start_date = models.DateField(verbose_name=u"Date d'arrivée")
    contact = models.CharField(verbose_name=u"Contact", max_length=200, blank=True, null=True, default=None)
    end_date = models.DateField(verbose_name=u"Date de départ",
        blank=True, null=True)
    created = models.DateTimeField(u'Création', auto_now_add=True)
    comment = models.TextField(max_length=3000,
        blank=True, null=True, verbose_name=u"Commentaire")


class InscriptionMotive(NamedAbstractModel):
    class Meta:
        verbose_name = u'Motif d\'inscription'
        verbose_name_plural = u'Motifs d\'inscription'


class Nationality(NamedAbstractModel):
    class Meta:
        verbose_name = u'Nationalité'
        verbose_name_plural = u'Nationalités'


class Job(NamedAbstractModel):
    class Meta:
        verbose_name = u'Profession'
        verbose_name_plural = u'Professions'


class RessourceQuerySet(query.QuerySet):
    def for_etablissement(self, etablissement):
        return self.filter(etablissement=etablissement)

    def for_service(self, service):
        return self.filter(etablissement__service=service)


class Ressource(NamedAbstractModel):
    objects = PassThroughManager.for_queryset_class(RessourceQuerySet)()
    etablissement = models.ForeignKey('Office')

    class Meta:
        verbose_name = u'Ressource'
        verbose_name_plural = u'Ressources'


class AnalyseMotive(NamedAbstractModel):
    class Meta:
        verbose_name = u"Motif analysé"
        verbose_name_plural = u"Motifs analysés"


class FamilyMotive(NamedAbstractModel):
    class Meta:
        verbose_name = u"Motif familiale"
        verbose_name_plural = u"Motifs familiaux"


class AdviceGiver(NamedAbstractModel):
    class Meta:
        verbose_name = u"Demandeur"
        verbose_name_plural = u"Demandeurs"


class Provenance(NamedAbstractModel):
    old_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID', blank=True, null=True)
    old_service = models.CharField(max_length=256,
            verbose_name=u'Ancien Service', blank=True, null=True)
    class Meta:
        verbose_name = u'Conseilleur'
        verbose_name_plural = u'Conseilleurs'


class ProvenancePlace(NamedAbstractModel):
    class Meta:
        verbose_name = u'Lieu de provenance'
        verbose_name_plural = u'Lieux de provenance'


class OutMotive(NamedAbstractModel):
    class Meta:
        verbose_name = u"Motif de sortie"
        verbose_name_plural = u"Motifs de sortie"


class OutTo(NamedAbstractModel):
    class Meta:
        verbose_name = u"Orientation de sortie"
        verbose_name_plural = u"Orientations de sortie"


class Service(NamedAbstractModel):
    admin_only = True

    slug = models.SlugField()
    description = models.TextField()

    # Contact
    phone = PhoneNumberField(verbose_name=u"Téléphone")
    fax = PhoneNumberField(verbose_name=u"Fax")
    email = models.EmailField()

    class Meta:
        verbose_name = u'Service'
        verbose_name_plural = u'Services'


class ActTypeQuerySet(query.QuerySet):
    def for_service(self, service):
        return self.filter(service=service)

class ActType(NamedAbstractModel, ServiceLinkedAbstractModel):
    objects = PassThroughManager.for_queryset_class(ActTypeQuerySet)()
    billable = models.BooleanField(default=True, verbose_name=u"Facturable")
    old_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID', blank=True, null=True)
    display_first = models.BooleanField(default=False, verbose_name=u"Acte principalement utilisé")
    group = models.BooleanField(default=False, verbose_name=u'En groupe')

    class Meta(NamedAbstractModel.Meta):
        verbose_name = u'Type d\'actes'
        verbose_name_plural = u'Types d\'actes'
        ordering = ('-display_first','name')

class ParentalAuthorityType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type d\'autorité parentale'
        verbose_name_plural = u'Types d\'autorités parentales'


class ParentalCustodyType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type de gardes parentales'
        verbose_name_plural = u'Types de gardes parentales'


class SessionType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type de séance'
        verbose_name_plural = u'Types de séances'


class FamilySituationType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type de situation familiale'
        verbose_name_plural = u'Types de situations familiales'


class MaritalStatusType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Régime matrimonial'
        verbose_name_plural = u'Régimes matrimoniaux'


class TransportType(NamedAbstractModel):
    class Meta:
        verbose_name = u'Type de transport'
        verbose_name_plural = u'Types de transports'


class WorkerType(NamedAbstractModel):
    intervene = models.BooleanField(
            verbose_name=u'Intervenant',
            default=True, blank=True)

    class Meta:
        verbose_name = u'Type de personnel'
        verbose_name_plural = u'Types de personnel'


AXIS =  Choices(
        (1, 'Axe I : catégories cliniques'),
        (2, 'Axe II : facteurs organiques'),
        (3, 'Axe II : facteurs environnementaux'),
)

class CodeCFTMEA(NamedAbstractModel):
    code = models.IntegerField(verbose_name=u"Code")
    axe = models.IntegerField(verbose_name=u"Axe", choices=AXIS,
            max_length=1)
    ordering_code = models.CharField(max_length=20, blank=True, null=True,
            verbose_name=u"Classification")

    def __unicode__(self):
        return "%s %s" % (self.ordering_code, self.name)

    class Meta:
        ordering = ['ordering_code']
        verbose_name = u'Code CFTMEA'
        verbose_name_plural = u'Codes CFTMEA'

class MDPH(models.Model):
    class Meta:
        verbose_name = u'Etablissement MDPH'
        verbose_name_plural = u'Etablissements MDPH'

    def __unicode__(self):
        return self.department

    department = models.CharField(max_length=200,
            verbose_name=u"Département")

    description = models.TextField(blank=True, null=True)

    # Contact
    phone = PhoneNumberField(verbose_name=u"Téléphone", blank=True, null=True)
    fax = PhoneNumberField(verbose_name=u"Fax", blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.CharField(max_length=200,
            verbose_name=u"Site Web", blank=True, null=True)

    # Address
    address = models.CharField(max_length=120,
            verbose_name=u"Adresse", blank=True, null=True)
    address_complement = models.CharField(max_length=120,
            blank=True,
            null=True,
            default=None,
            verbose_name=u"Complément d'addresse")
    zip_code = ZipCodeField(verbose_name=u"Code postal",
        blank=True, null=True)
    city = models.CharField(max_length=80,
            verbose_name=u"Ville", blank=True, null=True)

class MDPHRequest(models.Model):
    class Meta:
        verbose_name = u'Demande MDPH'
        verbose_name_plural = u'Demandes MDPH'

    start_date = models.DateField(verbose_name=u"Date de la demande")
    mdph = models.ForeignKey('ressources.MDPH',
            verbose_name=u"MDPH")
    comment = models.TextField(max_length=3000,
        blank=True, null=True, verbose_name=u"Commentaire")
    created = models.DateTimeField(u'Création', auto_now_add=True)

MDPH_HELP =  Choices(
        (0, "Non défini"),
        (1, "AEEH (Allocation d'éducation de l'enfant handicapé)"),
        (2, 'AVS (Assistant de vie scolaire)'),
        (3, 'EVS (Emplois de vie scolaire)'),
)

class MDPHResponse(models.Model):
    class Meta:
        verbose_name = u'Réponse MDPH'
        verbose_name_plural = u'Réponses MDPH'

    start_date = models.DateField(verbose_name=u"Date de début")
    end_date = models.DateField(verbose_name=u"Date de fin")
    mdph = models.ForeignKey('ressources.MDPH',
            verbose_name=u"MDPH")
    comment = models.TextField(max_length=3000,
        blank=True, null=True, verbose_name=u"Commentaire")
    created = models.DateTimeField(u'Création', auto_now_add=True)
    type_aide = models.IntegerField(verbose_name=u"Type d'aide", choices=MDPH_HELP,
            max_length=1, default=0)
    name =  models.CharField(max_length=200,
            verbose_name=u"Nom", blank=True, null=True)
    rate =  models.CharField(max_length=10,
            verbose_name=u"Taux", blank=True, null=True)


class HolidayType(NamedAbstractModel):
    for_group = models.BooleanField(
            verbose_name=u'Absence de groupe',
            default=True, blank=True)

    class Meta:
        verbose_name = u"Type d'absence"
        verbose_name_plural = u"Types d'absence"

class PatientRelatedLink(NamedAbstractModel):
    old_camsp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CAMSP', blank=True, null=True)
    old_cmpp_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au CMPP', blank=True, null=True)
    old_sessad_dys_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD TED', blank=True, null=True)
    old_sessad_ted_id = models.CharField(max_length=256,
            verbose_name=u'Ancien ID au SESSAD DYS', blank=True, null=True)
    class Meta:
        verbose_name = u'Type de lien avec le patient (parenté)'
        verbose_name_plural = u'Types de lien avec le patient (parenté)'

class PricePerAct(models.Model):
    price = models.DecimalField(verbose_name=u"Tarif", max_digits=5, decimal_places=2)
    start_date = models.DateField(verbose_name=u"Prise d'effet")

    class Pricing(object):
        def __init__(self, ppas):
            ppas = ppas.order_by('start_date')
            self.dates = [ppa.start_date for ppa in ppas]
            self.ppas = list(ppas)

        def price_at_date(self, date):
            i = bisect.bisect(self.dates, date)
            if i == 0:
                raise RuntimeError('No existing price at date %s' % date)
            return self.ppas[i-1].price

    class Meta:
        verbose_name = u"Tarif horaire de l'acte"
        verbose_name_plural = u"Tarifs horaires de l'acte"

    @classmethod
    def pricing(cls):
        return cls.Pricing(cls.objects.all())

    @classmethod
    def get_price(cls, at_date=None):
        if not at_date:
            at_date = date.today()
        if isinstance(at_date, datetime):
            at_date = date(day=at_date.day, month=at_date.month,
                year=at_date.year)
        found = cls.objects.filter(start_date__lte = at_date).latest('start_date')
        if not found:
            raise Exception('No price to apply')
        return found.price

    def __unicode__(self):
        return str(self.price) + ' (' + str(self.start_date) + ')'
