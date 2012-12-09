from django.contrib import admin

import reversion

from models import (ActType, CFTMEACode, FamilySituationType, HealthFund,
        InscriptionMotive, Job, Nationality, Office, ParentalAuthorityType,
        ParentalCustodyType, Room, School, SchoolTeacherRole,
        Service, SessionType, TransportCompany, TransportType,
        UninvoicableCode, WorkerType, LargeRegime)

admin.site.register(ActType, reversion.VersionAdmin)
admin.site.register(CFTMEACode, reversion.VersionAdmin)
admin.site.register(FamilySituationType, reversion.VersionAdmin)
admin.site.register(HealthFund, reversion.VersionAdmin)
admin.site.register(LargeRegime, reversion.VersionAdmin)
admin.site.register(InscriptionMotive, reversion.VersionAdmin)
admin.site.register(Job, reversion.VersionAdmin)
admin.site.register(Nationality, reversion.VersionAdmin)
admin.site.register(Office, reversion.VersionAdmin)
admin.site.register(ParentalAuthorityType, reversion.VersionAdmin)
admin.site.register(ParentalCustodyType, reversion.VersionAdmin)
admin.site.register(Room, reversion.VersionAdmin)
admin.site.register(School, reversion.VersionAdmin)
admin.site.register(SchoolTeacherRole, reversion.VersionAdmin)
admin.site.register(Service, reversion.VersionAdmin)
admin.site.register(SessionType, reversion.VersionAdmin)
admin.site.register(TransportCompany, reversion.VersionAdmin)
admin.site.register(TransportType, reversion.VersionAdmin)
admin.site.register(UninvoicableCode, reversion.VersionAdmin)
admin.site.register(WorkerType, reversion.VersionAdmin)
