# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from decimal import Decimal
from trytond.pool import Pool


class Subdiario(object):

    @classmethod
    def get_iva(cls, lines, type, group_tax='IVA'):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for line in lines:
            for invoice_tax in line.invoice_taxes:
                if type in invoice_tax.tax.name \
                   and group_tax.lower() in invoice_tax.tax.group.code.lower():
                    amount = Currency.round(line.invoice.currency, invoice_tax.amount)
                    break
        if line.invoice.type in ['out_credit_note', 'in_credit_note']:
            amount = amount * -1
        return amount

    @classmethod
    def get_iibb(cls, invoice, group_tax='iibb'):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group:
                if 'iibb' in invoice_tax.tax.group.code.lower():
                    amount = invoice.currency.round(invoice_tax.amount)
                    break
            else:
                raise ValueError('missing_tax_group %s ' % invoice_tax.rec_name)
        if invoice.type in ['out_credit_note', 'in_credit_note']:
            amount = amount * -1
        return amount

    @classmethod
    def get_iibb_name(cls, invoice, group_tax='iibb'):
        name = ''
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group:
                if 'iibb' in invoice_tax.tax.rec_name.lower():
                    name = invoice_tax.tax.rec_name
                    break
            else:
                raise ValueError('missing_tax_group %s ' % invoice_tax.rec_name)
        return name

    @classmethod
    def get_sum_neto_by_tax(cls, tax, invoices):
        Currency = Pool().get('currency.currency')
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax == tax:
                    untaxed_amount = invoice.untaxed_amount
                    if invoice.type in ['out_credit_note', 'in_credit_note']:
                        untaxed_amount = untaxed_amount * -1
                    if invoice.currency.id != invoice.company.id:
                        amount += Currency.compute(
                            invoice.currency, untaxed_amount, invoice.company.currency)
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
                    if invoice.type in ['out_credit_note', 'in_credit_note']:
                        tax_amount = tax_amount * -1
                    if invoice.currency.id != invoice.company.id:
                        amount += Currency.compute(
                            invoice.currency, tax_amount, invoice.company.currency)
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
                if invoice.type in ['out_credit_note', 'in_credit_note']:
                    untaxed_amount = untaxed_amount * -1
                if invoice.currency.id != invoice.company.id:
                    amount += Currency.compute(
                        invoice.currency, untaxed_amount, invoice.company.currency)
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
                    if 'iva' in invoice_tax.tax.group.code.lower():
                        tax_amount = invoice_tax.amount
                        if invoice.type in ['out_credit_note', 'in_credit_note']:
                            tax_amount = tax_amount * -1
                        if invoice.currency.id != invoice.company.id:
                            amount += Currency.compute(
                                invoice.currency, tax_amount, invoice.company.currency)
                        else:
                            amount += invoice.currency.round(tax_amount)
        return amount


    @classmethod
    def get_account(cls, lines):
        amounts = [(c.amount, c.account.rec_name) for c in lines]
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
                if line.invoice.type in ['out_credit_note', 'in_credit_note']:
                    line_amount = line_amount * -1
                amount = line_amount + amount
        return amount

    @classmethod
    def get_no_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            if line.invoice_taxes == ():
                line_amount = line.amount
                if line.invoice.type in ['out_credit_note', 'in_credit_note']:
                    line_amount = line_amount * -1
                amount = line_amount + amount
        return amount

    @classmethod
    def get_zona_iibb(cls, lines):
        impuestos_lst = [(c.invoice_taxes != (), c.invoice_taxes) for c in lines]
        zona = ''
        for key, values in impuestos_lst:
            if key:
                for impuesto in values:
                    if 'iibb' in impuesto.tax.group.code.lower():
                        zona = impuesto.tax.name
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
