# -*- coding: utf8 -*-
# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    subdivision = fields.Function(fields.Char('Subdivision'),
        'get_subdivision', searcher='search_subdivision')
    address = fields.Function(fields.Char('Address'), 'get_address')

    @classmethod
    def get_address(cls, invoices, name):
        res = {}
        for invoice in invoices:
            res[invoice.id] = ''
            if invoice.invoice_address:
                res[invoice.id] = ' '.join(
                    invoice.invoice_address.full_address.split('\n')[1:])
        return res

    @classmethod
    def get_subdivision(cls, invoices, name):
        res = {}
        for invoice in invoices:
            res[invoice.id] = ''
            if invoice.invoice_address:
                if hasattr(invoice.invoice_address, 'subdivision'):
                    if hasattr(invoice.invoice_address.subdivision, 'name'):
                        subdivision_name = (
                            invoice.invoice_address.subdivision.name)
                        res[invoice.id] = subdivision_name
        return res

    @classmethod
    def search_subdivision(cls, name, clause):
        return [('invoice_address.subdivision.name',) + tuple(clause[1:])]
