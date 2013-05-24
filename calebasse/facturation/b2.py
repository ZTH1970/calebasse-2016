# -*- coding: utf-8 -*-

# TODO / FIXME
# - lever une exception lorsque nb_lines dépasse 999 (et autres compteurs)

import os
import sys
import re
import glob
import tempfile
import time
import datetime
import hashlib
import base64
from smtplib import SMTP, SMTPException


from batches import build_batches
from transmission_utils import build_mail

OUTPUT_DIRECTORY = '/var/lib/calebasse/B2/'

#
# B2 informations
#
NORME = 'CP  '

TYPE_EMETTEUR = 'TE'
NUMERO_EMETTEUR = '420788606'
APPLICATION = 'TR'
MESSAGE = 'ENTROUVERT 0143350135 CALEBASSE 1301'
MESSAGE = MESSAGE + ' '*(37-len(MESSAGE))

CATEGORIE = '189'
STATUT = '60'
MODE_TARIF = '05'
NOM = 'CMPP SAINT ETIENNE'
NOM = NOM + ' '*(40-len(NOM))

#
# mailing
#
B2FILES = OUTPUT_DIRECTORY + '*-mail'
FROM = 'teletransmission@aps42.org'
SMTP_LOGIN = 'teletransmission'
SMTP_PASSWORD = os.environ.get('CALEBASSE_B2_SMTP_PASSWD')
# if there is a CALEBASSE_B2_DEBUG_TO environment variable, send all B2 mails
# to this address instead of real ones (yy.xxx@xxx.yy.rss.fr)
DEBUG_TO = os.environ.get('CALEBASSE_B2_DEBUG_TO')


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
    start_2 = '2' + NUMERO_EMETTEUR + ' ' + \
            invoice.policy_holder_social_security_id + \
            get_control_key(invoice.policy_holder_social_security_id) + \
            '000' + ('%0.9d' % invoice.number) + \
            '1' + ('%0.9d' % invoice.patient_id) + \
            invoice.policy_holder_healthcenter.large_regime.code + \
            invoice.policy_holder_healthcenter.dest_organism + \
            (invoice.policy_holder_other_health_center or '0000') + \
            '3' + b2date(start_date) + '000000' + \
            invoice.policy_holder_healthcenter.dest_organism + '000' + \
            '10' + '3' +  \
            b2date(start_date) + \
            '000000000' + ' ' + \
            b2date(invoice.patient_birthdate) + \
            ('%d' %  invoice.patient_twinning_rank)[-1:] + \
            b2date(start_date) + b2date(invoice.end_date) + '01' + \
            '00' + filler(10)
    write128(output_file, start_2)
    invoice_lines += 1
    nb_type3 = 0
    kind = invoice.first_tag[0]
    prestation = u'SNS  ' if kind == 'T' else u'SD   '
    for date in invoice.list_dates.split('$'):
        line_3 = '3' + NUMERO_EMETTEUR + ' ' + \
                invoice.policy_holder_social_security_id + \
                get_control_key(invoice.policy_holder_social_security_id) + \
                '000' + ('%0.9d' % invoice.number) + \
                '19' + '320' + \
                b2date(datetime.datetime.strptime(date, "%d/%m/%Y")) + \
                b2date(datetime.datetime.strptime(date, "%d/%m/%Y")) + \
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

def b2(seq_id, hc, batches):
    to = hc.b2_000()
    total = sum(b.total for b in batches)
    first_batch = min(b.number for b in batches)

    # B2 veut un identifiant de fichier sur 6 caractères alphanum
    hexdigest = hashlib.sha256('%s%s%s%s%s' % (seq_id, first_batch, NUMERO_EMETTEUR, to, total)).hexdigest()
    file_id = base64.encodestring(hexdigest).upper()[0:6]

    utcnow = datetime.datetime.utcnow()
    prefix = '%s-%s-%s-%s-%s.' % (seq_id, NUMERO_EMETTEUR, to, first_batch, file_id)
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

    if nb_lines > 990:
        # FIXME grouper les lots comme y fo pour que ca n'arrive jamais
        print "[FIXME] TROP DE LIGNES -- ", nb_lines
        raise

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

    b2_filename = os.path.join(OUTPUT_DIRECTORY, prefix + 'b2')
    os.rename(old_filename, b2_filename)

    # create S/MIME mail
    mail_filename = build_mail(hc.large_regime.code, hc.dest_organism, b2_filename)

    return b2_filename, mail_filename


def sendmail(mail):
    if DEBUG_TO:
        toaddr = DEBUG_TO
        print '(debug mode, sending to', toaddr, ')'
    else:
        toaddr = re.search('\nTo: +(.*)\n', mail, re.MULTILINE).group(1)
    fromaddr = FROM

    smtp = SMTP('mail.aps42.org',587)
    if DEBUG_TO:
        smtp.set_debuglevel(1)
    if SMTP_LOGIN:
        smtp.login(SMTP_LOGIN, SMTP_PASSWORD)
    ret = smtp.sendmail(fromaddr, toaddr, mail)
    smtp.close()
    return ret

def sendall():
    if not SMTP_PASSWORD:
        print 'CALEBASSE_B2_SMTP_PASSWD envvar is missing...'
        return
    for mail_filename in glob.glob(B2FILES):
        print 'sending', mail_filename
        mail = open(mail_filename).read()
        try:
            sendmail(mail)
        except SMTPException as e:
            print '        SMTP ERROR:', e
        else:
            print '        sent'
            os.rename(mail_filename, mail_filename + '-sent')
        time.sleep(10)


if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calebasse.settings")
    from calebasse.facturation.models import Invoicing

    if len(sys.argv) < 2:
        print 'just (re)send all mails...'
        sendall()
        sys.exit(0)

    try:
        invoicing = Invoicing.objects.filter(seq_id=sys.argv[1])[0]
    except IndexError:
        raise RuntimeError('Facture introuvable')
    print 'Facturation', invoicing.seq_id
    batches = build_batches(invoicing)
    for hc in batches:
        print 'pour', hc
        for b in batches[hc]:
            print '  lot', b
            b2_filename, mail_filename = b2(invoicing.seq_id, hc, [b])
            print '  B2    :', b2_filename
            print '  smime :', mail_filename
    sendall()

