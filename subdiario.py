# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from decimal import Decimal
from trytond.pool import Pool


class Subdiario(object):

    @classmethod
    def get_iva(cls, invoice, rate, group_tax='gravado'):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.rate and invoice_tax.tax.rate == Decimal(rate)
                    and invoice_tax.tax.group.afip_kind == 'gravado'):
                tax_amount = invoice_tax.amount
                if invoice.currency.id != invoice.company.currency.id:
                    amount += Currency.compute(
                        invoice.currency, tax_amount, invoice.company.currency)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_iibb(cls, invoice):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind == 'provincial':
                tax_amount = invoice_tax.amount
                if invoice.currency.id != invoice.company.currency.id:
                    amount += Currency.compute(
                        invoice.currency, tax_amount, invoice.company.currency)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_iibb_name(cls, invoice, group_tax='provincial'):
        name = ''
        one_tax = True
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind == 'provincial':
                if one_tax:
                    name = invoice_tax.tax.rec_name
                    one_tax = False
                else:
                    name += '| ' + invoice_tax.tax.rec_name
        return name

    @classmethod
    def get_other_taxes(cls, invoice):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind not in ('gravado', 'provincial'):
                tax_amount = invoice_tax.amount
                if invoice.currency.id != invoice.company.currency.id:
                    amount += Currency.compute(
                        invoice.currency, tax_amount, invoice.company.currency)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax(cls, tax, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax == tax:
                    untaxed_amount = invoice_tax.base
                    if invoice.currency.id != invoice.company.currency.id:
                        amount += Currency.compute(
                            invoice.currency, untaxed_amount,
                            invoice.company.currency)
                    else:
                        amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax(cls, tax, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax == tax:
                    tax_amount = invoice_tax.amount
                    if invoice.currency.id != invoice.company.currency.id:
                        amount += Currency.compute(
                            invoice.currency, tax_amount,
                            invoice.company.currency)
                    else:
                        amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_iva_condition(cls, iva_condition, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.party.iva_condition == iva_condition:
                untaxed_amount = invoice.untaxed_amount
                if invoice.currency.id != invoice.company.currency.id:
                    amount += Currency.compute(
                        invoice.currency, untaxed_amount,
                        invoice.company.currency)
                else:
                    amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_iva_condition(cls, iva_condition, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.party.iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax.group.afip_kind == 'gravado':
                        tax_amount = invoice_tax.amount
                        if invoice.currency.id != invoice.company.currency.id:
                            amount += Currency.compute(
                                invoice.currency, tax_amount,
                                invoice.company.currency)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.party.iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        untaxed_amount = invoice.untaxed_amount
                        if invoice.currency.id != invoice.company.currency.id:
                            amount += Currency.compute(
                                invoice.currency, untaxed_amount,
                                invoice.company.currency)
                        else:
                            amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.party.iva_condition == iva_condition:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        tax_amount = invoice_tax.amount
                        if invoice.currency.id != invoice.company.currency.id:
                            amount += Currency.compute(
                                invoice.currency, tax_amount,
                                invoice.company.currency)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_subdivision(cls, tax, subdivision, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision == subdivision:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        untaxed_amount = invoice.untaxed_amount
                        if invoice.currency.id != invoice.company.currency.id:
                            amount += Currency.compute(
                                invoice.currency, untaxed_amount,
                                invoice.company.currency)
                        else:
                            amount += invoice.currency.round(untaxed_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_subdivision(cls, tax, subdivision,
            invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision == subdivision:
                for invoice_tax in invoice.taxes:
                    if invoice_tax.tax == tax:
                        tax_amount = invoice_tax.amount
                        if invoice.currency.id != invoice.company.currency.id:
                            amount += Currency.compute(
                                invoice.currency, tax_amount,
                                invoice.company.currency)
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
            if invoice_tax.tax.group.afip_kind == 'provincial':
                if invoice.subdivision == '':
                    zona = 'Subdivision is missing %s' % invoice.party
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
