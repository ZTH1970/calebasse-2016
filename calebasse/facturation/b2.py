# -*- coding: utf-8 -*-

# TODO / FIXME
# - code CCCC dans le type 2
# - lever une exception lorsque nb_lines dépasse 999 (et autres compteurs)

import os
import sys
import tempfile
import datetime
import hashlib
import base64

from batches import build_batches

#OUTPUT_DIRECTORY = '/var/lib/calebasse/B2/'
OUTPUT_DIRECTORY = '/var/tmp/'

NORME = 'CP  '

TYPE_EMETTEUR = 'TE'
NUMERO_EMETTEUR = '420788606'
APPLICATION = 'TR'
MESSAGE = 'ENTROUVERT CALEBASSE V 2013 1'
MESSAGE = MESSAGE + ' '*(37-len(MESSAGE))

CATEGORIE = '189'
STATUT = '60'
MODE_TARIF = '05'
NOM = 'CMPP SAINT ETIENNE'
NOM = NOM + ' '*(40-len(NOM))


def filler(n, car=' '):
    return car*n
def filler0(n):
    return filler(n, '0')
def b2date(d):
    return d.strftime('%y%m%d')
def get_control_key(nir):
    try:
        # Corse dpt 2A et 2B
        minus = 0
        if nir[6] in ('A', 'a'):
            nir = [c for c in nir]
            nir[6] = '0'
            nir = ''.join(nir)
            minus = 1000000
        elif nir[6] in ('B', 'b'):
            nir = [c for c in nir]
            nir[6] = '0'
            nir = ''.join(nir)
            minus = 2000000
        nir = int(nir) - minus
        return '%0.2d' % (97 - (nir % 97))
    except Exception, e:
        return '00'


def write128(output_file, line):
    if len(line) != 128:
        raise RuntimeError('length of this B2 line is %d != 128 : <<%s>>' %
                (len(line), line))
    output_file.write(line)

def write_invoice(output_file, invoice):
    invoice_lines = 0
    start_date = invoice.start_date
    # FIXME IMPORTANT/URGENT -- CCCC = other_ de policy_holder à ajouter dans
    # le modele invoice
    start_2 = '2' + NUMERO_EMETTEUR + ' ' + \
            invoice.policy_holder_social_security_id + \
            get_control_key(invoice.policy_holder_social_security_id) + \
            '000' + ('%0.9d' % invoice.number) + \
            '1' + ('%0.9d' % invoice.patient_id) + \
            invoice.policy_holder_healthcenter.large_regime.code + \
            invoice.policy_holder_healthcenter.dest_organism + \
            'CCCC' + \
            '1' + b2date(start_date) + '000000' + \
            invoice.policy_holder_healthcenter.dest_organism + '000' + \
            '10' + ' ' +  \
            b2date(start_date) + \
            '000000000' + ' ' + \
            b2date(invoice.patient_birthdate) + \
            ('%d' %  invoice.patient_twinning_rank)[-1:] + \
            b2date(start_date) + b2date(invoice.end_date) + '01' + \
            '00' + filler(10)
    write128(output_file, start_2)
    invoice_lines += 1
    nb_type3 = 0
    for act in invoice.acts.all():
        prestation = u'SNS  ' if act.get_hc_tag().startswith('T') else u'SD   '
        line_3 = '3' + NUMERO_EMETTEUR + ' ' + \
                invoice.policy_holder_social_security_id + \
                get_control_key(invoice.policy_holder_social_security_id) + \
                '000' + ('%0.9d' % invoice.number) + \
                '19' + '320' + \
                b2date(act.date) + b2date(act.date) + \
                prestation + '001' + \
                ' ' + '00100' +  ' ' + '00000' + \
                ('%0.7d' % invoice.ppa) + \
                ('%0.8d' % invoice.ppa) + \
                '100' + \
                ('%0.8d' % invoice.ppa) + \
                ('%0.8d' % invoice.ppa) + \
                '0000' + '000' + ' ' + filler(2) + ' ' + \
                ' ' + '0000000'
        write128(output_file, line_3)
        invoice_lines += 1
        nb_type3 += 1

    end_5 = '5' + NUMERO_EMETTEUR + ' ' + \
            invoice.policy_holder_social_security_id + \
            get_control_key(invoice.policy_holder_social_security_id) + \
            '000' + ('%0.9d' % invoice.number) + \
            ('%0.3d' % nb_type3) + \
            ('%0.8d' % invoice.amount) + \
            ('%0.8d' % invoice.amount) + \
            '00000000' + '00000000' + '00000000' + '00000000' + '00000000' + \
            filler(17) + \
            ('%0.8d' % invoice.amount) + \
            filler(4+2)
    write128(output_file, end_5)
    invoice_lines += 1

    return invoice_lines

def b2(seq_id, batches):
    to = batches[0].health_center.b2_000()
    total = sum(b.total for b in batches)

    # B2 veut un identifiant de fichier sur 6 caractères alphanum
    hexdigest = hashlib.sha256('%s%s%s%s' % (seq_id, NUMERO_EMETTEUR, to, total)).hexdigest()
    file_id = base64.encodestring(hexdigest).upper()[0:6]

    utcnow = datetime.datetime.utcnow()
    prefix = '%s-%s-%s-%s.' % (NUMERO_EMETTEUR, utcnow.strftime('%y%m%d%H%M'), to,
            file_id)
    output_file = tempfile.NamedTemporaryFile(suffix='.b2tmp',
            prefix=prefix, dir=OUTPUT_DIRECTORY, delete=False)
    nb_lines = 0

    start_000 = '000' +  TYPE_EMETTEUR + '00000' + NUMERO_EMETTEUR + \
            filler(6) + to + filler(6) + APPLICATION + \
            file_id + b2date(utcnow) + NORME + 'B2' + filler(15) + \
            '128' + filler(6) + MESSAGE
    write128(output_file, start_000)
    nb_lines += 1
    nb_batches = 0

    for batch in batches:
        start_1 = '1' + NUMERO_EMETTEUR + filler(6) + \
                batch.health_center.dest_organism[0:3] + \
                ('%0.3d' % batch.number) + CATEGORIE + STATUT + MODE_TARIF + \
                NOM + 'B2' + b2date(utcnow) + ' ' + NORME[0:2] + \
                ' ' + '062007' + 'U' + filler(2+3+1+34)
        write128(output_file, start_1)
        nb_lines += 1

        for i in batch.invoices:
            nb_lines += write_invoice(output_file, i)

        end_6 = '6' + NUMERO_EMETTEUR + \
                ('%0.3d' % batch.number_of_invoices) + \
                ('%0.4d' % batch.number_of_acts) + \
                ('%0.4d' % batch.number_of_invoices) + \
                ('%0.3d' % batch.number_of_invoices) + \
                ('%0.9d' % (batch.total * 100)) + \
                ('%0.9d' % (batch.total * 100)) + \
                '000000000' + ('%0.3d' % batch.number) + \
                filler(1+1+4+12+12+3+9+32)
        write128(output_file, end_6)
        nb_lines += 1
        nb_batches += 1

    end_999 = '999' +  TYPE_EMETTEUR + '00000' + NUMERO_EMETTEUR + \
            filler(6) + to + filler(6) + APPLICATION + \
            file_id + \
            ('%0.8d' % (nb_lines+1)) + \
            filler(19) + \
            ('%0.3d' % nb_batches) + \
            filler(43)
    write128(output_file, end_999)

    old_filename = output_file.name
    output_file.close()

    filename = os.path.join(OUTPUT_DIRECTORY, prefix + 'b2')
    os.rename(old_filename, filename)
    return filename

if __name__ == '__main__':
    sys.path.append('/home/thomas/dev/aps42/ve/calebasse')
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calebasse.settings")
    from calebasse.facturation.models import Invoicing

    invoicing = Invoicing.objects.filter(seq_id=sys.argv[1])[0]
    print 'Facturation', invoicing.seq_id
    batches = build_batches(invoicing)
    for hc in batches:
        print b2(invoicing.seq_id, batches[hc])

