# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import stdnum.ar.cuit as cuit
import stdnum.ar.dni as dni
from pysimplesoap.client import SimpleXMLElement
from unidecode import unidecode
from decimal import Decimal

from trytond.pool import Pool
from trytond.transaction import Transaction

class Subdiario(object):

    @classmethod
    def format_ci(cls, iva_condition):
        iva_condition = iva_condition.lower()
        if iva_condition in ('exento', 'monotributo'):
            return iva_condition.upper()[:2]
        else:
            if '_' in iva_condition:
                first, second = iva_condition.split('_')
            else:
                first, second = iva_condition.split(' ')
            return  '%s%s' % (first[:1].upper(), second[:1].upper())

    @classmethod
    def get_amount(cls, invoice, field):
        Currency = Pool().get('currency.currency')
        value = getattr(invoice, field)
        amount = value
        if invoice.currency != invoice.company.currency:
            amount = cls.get_secondary_amount(invoice, value)
        return amount

    @classmethod
    def get_secondary_amount(cls, invoice, value):
        Currency = Pool().get('currency.currency')
        if invoice.pos and invoice.pos.pos_type == 'electronic':
            afip_tr, = [tr for tr in invoice.transactions
                if tr.pyafipws_result=='A']
            request = SimpleXMLElement(unidecode(afip_tr.pyafipws_xml_request))
            if invoice.pos.pyafipws_electronic_invoice_service == 'wsfex':
                ctz = Decimal(str(request('Moneda_ctz')))
            elif invoice.pos.pyafipws_electronic_invoice_service == 'wsfe':
                ctz = Decimal(str(request('MonCotiz')))
        currency_rate = invoice.currency_rate or ctz
        context = dict(date=invoice.currency_date)
        if currency_rate:
            context['currency_rate'] = currency_rate
        with Transaction().set_context(context):
            amount = Currency.compute(invoice.currency, value,
                invoice.company.currency)
        return amount

    @classmethod
    def get_iva_condition(cls, invoice):
        return (cls.format_ci(invoice.party_iva_condition
                or invoice.party.iva_condition))

    @classmethod
    def get_party_tax_identifier(cls, invoice):
        code = ''
        if invoice.party.vat_number:
            code = invoice.party.vat_number
        elif invoice.party.vat_number_afip_foreign:
            code = invoice.party.vat_number_afip_foreign
        else:
            for identifier in invoice.party.identifiers:
                if identifier.type == 'ar_dni':
                    code = identifier.code

        if cuit.is_valid(code):
            code = cuit.format(code)
        elif dni.is_valid(code):
            code = dni.format(code)
        return code

    @classmethod
    def get_iva(cls, invoice, rate, group_tax='IVA'):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.rate and invoice_tax.tax.rate == Decimal(rate)
                    and invoice_tax.tax.group
                    and group_tax.lower() in invoice_tax.tax.group.code.lower()):
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_iibb(cls, invoice):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.group and 'iibb' in
                    invoice_tax.tax.group.code.lower()):
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_iibb_name(cls, invoice, group_tax='iibb'):
        name = ''
        one_tax = True
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.group and 'iibb' in
                    invoice_tax.tax.group.code.lower()):
                if one_tax:
                    name = invoice_tax.tax.rec_name
                    one_tax = False
                else:
                    name += '| ' + invoice_tax.tax.rec_name
        return name

    @classmethod
    def get_other_taxes(cls, invoice):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.group and invoice_tax.tax.group.code.lower()
                    not in ['iibb', 'iva']):
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax(cls, tax, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax == tax:
                    untaxed_amount = invoice_tax.base
                    if invoice.currency != invoice.company.currency:
                        amount += cls.get_secondary_amount(invoice, untaxed_amount)
                    else:
                        amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax(cls, tax, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax == tax:
                    tax_amount = invoice_tax.amount
                    if invoice.currency != invoice.company.currency:
                        amount += cls.get_secondary_amount(invoice, tax_amount)
                    else:
                        amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_iva_condition(cls, iva_condition, invoices):
        amount = Decimal('0')

        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition
                or invoice.party.iva_condition)
            if party_iva_condition == iva_condition:
                untaxed_amount = invoice.untaxed_amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, untaxed_amount)
                else:
                    amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_iva_condition(cls, iva_condition, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition
                or invoice.party.iva_condition)
            if party_iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if (invoice_tax.tax.group and 'iva' in
                            invoice_tax.tax.group.code.lower()):
                        tax_amount = invoice_tax.amount
                        if invoice.currency != invoice.company.currency:
                            amount += cls.get_secondary_amount(invoice,
                                tax_amount)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition
                or invoice.party.iva_condition)
            if party_iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        untaxed_amount = invoice.untaxed_amount
                        if invoice.currency != invoice.company.currency:
                            amount += cls.get_secondary_amount(invoice,
                                untaxed_amount)
                        else:
                            amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition
                or invoice.party.iva_condition)
            if party_iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        tax_amount = invoice_tax.amount
                        if invoice.currency != invoice.company.currency:
                            amount += cls.get_secondary_amount(invoice,
                                tax_amount)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_subdivision(cls, tax, subdivision, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision == subdivision:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        untaxed_amount = invoice.untaxed_amount
                        if invoice.currency != invoice.company.currency:
                            amount += cls.get_secondary_amount(invoice,
                                untaxed_amount)
                        else:
                            amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_subdivision(cls, tax, subdivision,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision == subdivision:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        tax_amount = invoice_tax.amount
                        if invoice.currency != invoice.company.currency:
                            amount += cls.get_secondary_amount(invoice,
                                tax_amount)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_account(cls, lines):
        amounts = [(abs(c.amount), c.account.rec_name) for c in lines]
        concepto_amount = Decimal('0')
        concepto = ''
        for amount, description in amounts:
            if amount >= concepto_amount:
                amount = concepto_amount
                concepto = description
        return concepto

    @classmethod
    def get_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            if line.invoice_taxes:
                line_amount = line.amount
                amount = line_amount + amount
        return amount

    @classmethod
    def get_no_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            if line.invoice_taxes == ():
                line_amount = line.amount
                amount = line_amount + amount
        return amount

    @classmethod
    def get_zona_iibb(cls, invoice):
        zona = ''
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.group and 'iibb' in
                    invoice_tax.tax.group.code.lower()):
                if invoice.subdivision == '':
                    zona = 'The subdivision is missing at party %s' % invoice.party
                else:
                    zona = invoice.subdivision
        return zona

    @classmethod
    def get_concepto(cls, lines):
        amounts = [(c.amount, c.description) for c in lines]
        concepto_amount = Decimal('0')
        concepto = ''
        for amount, description in amounts:
            if amount >= concepto_amount:
                amount = concepto_amount
                concepto = description
        return concepto
