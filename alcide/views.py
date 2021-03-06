# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect
from django.template.defaultfilters import slugify

from cbv import HOME_SERVICE_COOKIE, TemplateView

from alcide.ressources.models import Service
from alcide.middleware.request import get_request
from alcide.utils import is_validator


APPLICATIONS = (
        (u'Gestion des dossiers', 'dossiers', False),
        (u'Agenda', 'agenda', False),
        (u'Saisie des actes', 'actes', True),
        (u'Facturation et décompte', 'facturation', True),
        (u'Gestion des personnes', 'personnes', True),
        (u'Gestion des ressources', 'ressources', True),
        (u'Statistiques', 'statistics', True),
)

def redirect_to_homepage(request):
    service_name = request.COOKIES.get(HOME_SERVICE_COOKIE, 'cmpp').lower()
    return redirect('homepage', service=service_name)

class Homepage(TemplateView):
    template_name='alcide/homepage.html'
    cookies_to_clear = [('agenda-tabs', )]

    def dispatch(self, request, **kwargs):
        if 'service' in kwargs:
            self.cookies_to_clear = [('agenda-tabs',
                                      '/%s/agenda' % kwargs['service']),
                                     ('active-agenda',
                                      '/%s/agenda' % kwargs['service']),
                                     ('last-ressource',
                                      '/%s/agenda' % kwargs['service']),
                                     ]
        return super(Homepage, self).dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        services = Service.objects.values_list('name', 'slug')
        services = sorted(services, key=lambda tup: tup[0])
        ctx = super(Homepage, self).get_context_data(**kwargs)
        applications = list(APPLICATIONS)
        ctx.update({
            'applications': applications,
            'services': services,
            'service_name': self.service.name,
        })
        return ctx

homepage = Homepage.as_view()
