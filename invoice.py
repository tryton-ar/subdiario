# -*- coding: utf8 -*-
# This file is part of subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateView, Button, StateReport
from trytond.transaction import Transaction
from trytond.report import Report

from decimal import Decimal
from .subdiario import Subdiario

_ZERO = Decimal('0.0')


__all__ = ['Invoice', 'SubdiarioPurchaseStart', 'SubdiarioSaleStart',
    'SubdiarioPurchase', 'SubdiarioSale', 'SubdiarioPurchaseReport',
    'SubdiarioSaleReport', 'SubdiarioSaleType', 'SubdiarioSaleTypeReport',
    'SubdiarioSaleSubdivision', 'SubdiarioSaleSubdivisionReport']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    subdivision = fields.Function(fields.Char('Subdivision'),
        'get_subdivision', searcher='search_subdivision')
    address = fields.Function(fields.Char('Address'), 'get_address')

    @classmethod
    def get_address(cls, invoices, name):
        res = {}
        for invoice in cls.browse(invoices):
            res[invoice.id] = ''
            if invoice.invoice_address:
                res[invoice.id] = ' '.join(
                    invoice.invoice_address.full_address.split('\n')[1:])
        return res

    @classmethod
    def get_subdivision(cls, invoices, name):
        res = {}
        for invoice in cls.browse(invoices):
            res[invoice.id] = ''
            if invoice.invoice_address:
                if hasattr(invoice.invoice_address, 'subdivision'):
                    if hasattr(invoice.invoice_address.subdivision, 'name'):
                        subdivision_name = \
                            invoice.invoice_address.subdivision.name
                        res[invoice.id] = subdivision_name
        return res

    @classmethod
    def search_subdivision(cls, name, clause):
        return [('invoice_address.subdivision.name',) + tuple(clause[1:])]


class SubdiarioPurchaseStart(ModelView):
    'SubdiarioPurchaseStart'
    __name__ = 'subdiario.purchase.start'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_from_date():
        import datetime
        Date = Pool().get('ir.date')
        return datetime.date(Date.today().year, 1, 1)

    @staticmethod
    def default_to_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


class SubdiarioPurchase(Wizard):
    'SubdiarioPurchase '
    __name__ = 'subdiario.purchase'
    start = StateView('subdiario.purchase.start',
        'subdiario.purchase_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'print_', 'tryton-print', True),
            ])
    print_ = StateReport('subdiario.purchase_report')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            }
        return action, data


class SubdiarioPurchaseReport(Report, Subdiario):
    'SubdiarioPurchaseReport'
    __name__ = 'subdiario.purchase_report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Tax = pool.get('account.tax')
        Company = pool.get('company.company')
        Subdivision = pool.get('country.subdivision')
        total_amount = Decimal('0')
        total_untaxed_amount = Decimal('0')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'in'),
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ], order=[('invoice_date', 'ASC')])

        taxes = Tax.search([
            ('group.kind', 'in', ['purchase', 'both']),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        alicuotas = Tax.search([
            ('group.kind', '=', 'purchase'),
            ('group.afip_kind', '=', 'gravado'),
            ], order=[('name', 'ASC')])

        iibb_taxes = Tax.search([
            ('group.kind', 'in', ['purchase', 'both']),
            ('group.afip_kind', '=', 'provincial'),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        company = Company(data['company'])
        for invoice in invoices:
            total_amount = invoice.total_amount + total_amount
            total_untaxed_amount = (invoice.untaxed_amount +
                total_untaxed_amount)

        iva_conditions = [
            'responsable_inscripto',
            'exento',
            'consumidor_final',
            'monotributo',
            'no_alcanzado',
            ]

        subdivisions = Subdivision.search([
            ('country.code', '=', 'AR')
            ], order=[('name', 'ASC')])

        report_context = super(SubdiarioPurchaseReport,
            cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['invoices'] = invoices
        report_context['subdivisions'] = subdivisions
        report_context['total_amount'] = total_amount
        report_context['total_untaxed_amount'] = total_untaxed_amount
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_other_taxes'] = cls.get_other_taxes
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_zona_iibb'] = cls.get_zona_iibb
        report_context['get_concepto'] = cls.get_concepto
        report_context['get_account'] = cls.get_account
        report_context['taxes'] = taxes
        report_context['alicuotas'] = alicuotas
        report_context['iva_conditions'] = iva_conditions
        report_context['iibb_taxes'] = iibb_taxes
        report_context['get_sum_neto_by_tax'] = cls.get_sum_neto_by_tax
        report_context['get_sum_percibido_by_tax'] = \
            cls.get_sum_percibido_by_tax
        report_context['get_sum_neto_by_iva_condition'] = \
            cls.get_sum_neto_by_iva_condition
        report_context['get_sum_percibido_by_iva_condition'] = \
            cls.get_sum_percibido_by_iva_condition
        report_context['get_sum_neto_by_tax_and_iva_condition'] = \
            cls.get_sum_neto_by_tax_and_iva_condition
        report_context['get_sum_percibido_by_tax_and_iva_condition'] = \
            cls.get_sum_percibido_by_tax_and_iva_condition
        report_context['get_sum_neto_by_tax_and_subdivision'] = \
            cls.get_sum_neto_by_tax_and_subdivision
        report_context['get_sum_percibido_by_tax_and_subdivision'] = \
            cls.get_sum_percibido_by_tax_and_subdivision

        return report_context

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        Invoice = Pool().get('account.invoice')
        return '%s - %s' % (tipo_cpte,
            dict(Invoice._fields['tipo_comprobante'].selection)[tipo_cpte])


class SubdiarioSaleStart(ModelView):
    'SubdiarioSaleStart'
    __name__ = 'subdiario.sale.start'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    pos = fields.Many2Many('account.pos', None, None, 'Points of Sale',
        required=True, help="Por defecto puntos de venta electronicos")

    @staticmethod
    def default_from_date():
        import datetime
        Date = Pool().get('ir.date')
        return datetime.date(Date.today().year, 1, 1)

    @staticmethod
    def default_to_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_pos():
        Pos = Pool().get('account.pos')
        company_id = Transaction().context.get('company', -1)
        pos = Pos.search([
            ('pos_type', '=', 'electronic'),
            ('pos_do_not_report', '=', False),
            ('company', '=', company_id),
            ])
        return [p.id for p in pos]


class SubdiarioSale(Wizard):
    'Post Invoices'
    __name__ = 'subdiario.sale'
    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'print_', 'tryton-print', True),
            ])
    print_ = StateReport('subdiario.sale_report')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'pos': [p.id for p in self.start.pos],
            }
        return action, data


class SubdiarioSaleReport(Report, Subdiario):
    'SubdiarioSaleReport'
    __name__ = 'subdiario.sale_report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Tax = pool.get('account.tax')
        Company = pool.get('company.company')
        total_amount = _ZERO
        total_untaxed_amount = _ZERO
        totales_amount = _ZERO
        totales_untaxed_amount = _ZERO
        totales_iva105 = _ZERO
        totales_iva21 = _ZERO
        totales_iva27 = _ZERO

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', 'in', data['pos']),
            ], order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        company = Company(data['company'])

        for invoice in invoices:
            total_amount = invoice.total_amount + total_amount
            total_untaxed_amount = (invoice.untaxed_amount +
                total_untaxed_amount)
        for invoice in invoices:
            totales_amount += cls.get_amount(invoice, 'total_amount')
            totales_untaxed_amount += cls.get_amount(invoice, 'untaxed_amount')
            totales_iva21 += cls.get_iva(invoice, '0.21')
            totales_iva105 += cls.get_iva(invoice, '0.105')
            totales_iva27 += cls.get_iva(invoice, '0.27')

        taxes = Tax.search([
            ('group.kind', 'in', ['sale', 'both']),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        alicuotas = Tax.search([
            ('group.kind', '=', 'sale'),
            ('group.afip_kind', '=', 'gravado'),
            ], order=[('name', 'ASC')])

        iva_conditions = [
            'responsable_inscripto',
            'exento',
            'consumidor_final',
            'monotributo',
            'no_alcanzado',
            ]

        report_context = super(SubdiarioSaleReport,
            cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['invoices'] = invoices
        report_context['format_ci'] = cls.format_ci
        report_context['get_iva'] = cls.get_iva
        report_context['get_iva_condition'] = cls.get_iva_condition
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['get_amount'] = cls.get_amount
        report_context['get_account'] = cls.get_account
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iibb_name'] = cls.get_iibb_name
        report_context['taxes'] = taxes
        report_context['alicuotas'] = alicuotas
        report_context['iva_conditions'] = iva_conditions
        report_context['totales_amount'] = totales_amount
        report_context['totales_untaxed_amount'] = totales_untaxed_amount
        report_context['totales_iva105'] = totales_iva105
        report_context['totales_iva21'] = totales_iva21
        report_context['totales_iva27'] = totales_iva27
        report_context['get_sum_neto_by_tax'] = cls.get_sum_neto_by_tax
        report_context['get_sum_percibido_by_tax'] = (
            cls.get_sum_percibido_by_tax)
        report_context['get_sum_neto_by_iva_condition'] = (
            cls.get_sum_neto_by_iva_condition)
        report_context['get_sum_percibido_by_iva_condition'] = (
            cls.get_sum_percibido_by_iva_condition)
        report_context['get_sum_neto_by_tax_and_iva_condition'] = (
            cls.get_sum_neto_by_tax_and_iva_condition)
        report_context['get_sum_percibido_by_tax_and_iva_condition'] = (
            cls.get_sum_percibido_by_tax_and_iva_condition)
        return report_context


class SubdiarioSaleType(Wizard):
    'SubdiarioSaleType'
    __name__ = 'subdiario.sale.type'
    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'print_', 'tryton-print', True),
            ])
    print_ = StateReport('subdiario.sale_type_report')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'pos': [p.id for p in self.start.pos],
            }
        return action, data


class SubdiarioSaleTypeReport(Report, Subdiario):
    'SubdiarioSaleTypeReport'
    __name__ = 'subdiario.sale_type_report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Company = pool.get('company.company')
        PosSequence = pool.get('account.pos.sequence')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', 'in', data['pos']),
            ], order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        company = Company(data['company'])
        pos_sequences = PosSequence.search([
            ('pos', 'in', data['pos'])
            ])

        report_context = super(SubdiarioSaleTypeReport,
            cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['tipos_cptes'] = pos_sequences
        report_context['invoices'] = invoices
        report_context['get_iva'] = cls.get_iva
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iva_condition'] = cls.get_iva_condition
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['get_amount'] = cls.get_amount
        report_context['format_ci'] = cls.format_ci
        return report_context


class SubdiarioSaleSubdivision(Wizard):
    'Post Invoices'
    __name__ = 'subdiario.sale.subdivision'
    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('OK', 'print_', 'tryton-print', True),
            ])
    print_ = StateReport('subdiario.sale_subdivision_report')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'pos': [p.id for p in self.start.pos],
            }
        return action, data


class SubdiarioSaleSubdivisionReport(Report, Subdiario):
    __name__ = 'subdiario.sale_subdivision_report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Company = pool.get('company.company')
        Subdivision = pool.get('country.subdivision')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', 'in', data['pos']),
            ], order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        company = Company(data['company'])
        # search subdivisions of Argentina
        subdivisions = Subdivision.search([
            ('country.code', '=', 'AR')
            ], order=[('name', 'ASC')])

        report_context = super(SubdiarioSaleSubdivisionReport,
            cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['subdivisions'] = subdivisions
        report_context['invoices'] = invoices
        report_context['get_iva'] = cls.get_iva
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iva_condition'] = cls.get_iva_condition
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['get_amount'] = cls.get_amount
        report_context['format_ci'] = cls.format_ci
        return report_context
