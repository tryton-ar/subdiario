# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from decimal import Decimal


class Subdiario:

    @classmethod
    def get_iva(cls, lines, type, group_tax='IVA'):
        amount = Decimal('0')
        for line in lines:
            for invoice_tax in line.invoice_taxes:
                if type in invoice_tax.tax.name \
                        and invoice_tax.tax.group.name == group_tax:
                    amount = invoice_tax.amount
                    break
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
                amount = line.amount + amount
        return amount

    @classmethod
    def get_no_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            if line.invoice_taxes == ():
                amount = line.amount + amount
        return amount

    @classmethod
    def get_zona_iibb(cls, lines):
        impuestos_lst = [(c.invoice_taxes != (), c.invoice_taxes) for c in lines]
        zona = ''
        for key, values in impuestos_lst:
            if key:
                for impuesto in values:
                    if 'PERCEPCION' in impuesto.tax.group.name:
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
