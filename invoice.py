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
from subdiario import Subdiario


__all__ = ['Invoice', 'SubdiarioPurchaseStart', 'SubdiarioSaleStart',
           'SubdiarioPurchase', 'SubdiarioSale', 'SubdiarioPurchaseReport',
           'SubdiarioSaleReport', 'SubdiarioSaleType',
           'SubdiarioSaleTypeReport', 'SubdiarioSaleSubdivision',
           'SubdiarioSaleSubdivisionReport']
__metaclass__ = PoolMeta


class Invoice:
    __name__ = 'account.invoice'

    subdiario_type = fields.Selection([
        ('', ''),
        ('goods', 'Goods'),
        ('service', 'Service'),
        ('localtion', 'Location'),
    ], 'Subdiario type')
    subdivision = fields.Function(fields.Char('Subdivision'),
                                  'get_subdivision',
                                  searcher='search_subdivision')
    address = fields.Function(fields.Char('Address'), 'get_address')

    @classmethod
    def get_address(cls, invoices, name):
        res = {}
        for invoice in cls.browse(invoices):
            res[invoice.id] = ''
            if invoice.invoice_address:
                res[invoice.id] = ' '.join(invoice.invoice_address.full_address.split('\n')[1:])
        return res

    @classmethod
    def get_subdivision(cls, invoices, name):
        res = {}
        for invoice in cls.browse(invoices):
            res[invoice.id] = ''
            if invoice.invoice_address:
                if hasattr(invoice.invoice_address, 'subdivision'):
                    if hasattr(invoice.invoice_address.subdivision, 'name'):
                        subdivision_name = invoice.invoice_address.subdivision.name
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
        total_amount = Decimal('0')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'in'),
            ('invoice_date', '>=', data['from_date']),
            ('invoice_date', '<=', data['to_date']),
            ('company', '=', data['company']),
        ], order=[('invoice_date', 'ASC')])

        taxes = Tax.search([
            ('group.kind', 'in', ['purchase', 'both']),
        ], order=[('name', 'ASC')])


        company = Company(data['company'])
        for invoice in invoices:
            total_amount = invoice.total_amount + total_amount

        report_context = super(SubdiarioPurchaseReport, cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['invoices'] = invoices
        report_context['total_amount'] = total_amount
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_zona_iibb'] = cls.get_zona_iibb
        report_context['get_concepto'] = cls.get_concepto
        report_context['get_account'] = cls.get_account
        report_context['taxes'] = taxes
        report_context['get_sum_neto_by_tax'] = cls.get_sum_neto_by_tax
        report_context['get_sum_percibido_by_tax'] = cls.get_sum_percibido_by_tax

        return report_context

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        Invoice = Pool().get('account.invoice')
        return tipo_cpte + ' - ' + \
            dict(Invoice._fields['tipo_comprobante'].selection)[tipo_cpte]


class SubdiarioSaleStart(ModelView):
    'SubdiarioSaleStart'
    __name__ = 'subdiario.sale.start'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    pos = fields.Many2One('account.pos', 'Point of Sale', required=True)

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
        pos = Pos.search([
            ('pos_type', '=', 'electronic'),
            ('pyafipws_electronic_invoice_service', '=', 'wsfe'),
        ])
        if pos != []:
            pos = pos[0].id
        else:
            pos = None
        return pos


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
            'pos': self.start.pos.id,
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
        Pos = pool.get('account.pos')
        total_amount = Decimal('0')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('invoice_date', '>=', data['from_date']),
            ('invoice_date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', '=', data['pos']),
        ], order=[('number', 'ASC')])

        company = Company(data['company'])
        pos = Pos(data['pos'])
        for invoice in invoices:
            total_amount = invoice.total_amount + total_amount

        taxes = Tax.search([
            ('group.kind', 'in', ['sale', 'both']),
        ], order=[('name', 'ASC')])

        report_context = super(SubdiarioSaleReport, cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['pos'] = pos
        report_context['invoices'] = invoices
        report_context['total_amount'] = total_amount
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_iva'] = cls.get_iva
        report_context['get_account'] = cls.get_account
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iibb_name'] = cls.get_iibb_name
        report_context['taxes'] = taxes
        report_context['get_sum_neto_by_tax'] = cls.get_sum_neto_by_tax
        report_context['get_sum_percibido_by_tax'] = cls.get_sum_percibido_by_tax
        return report_context

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        return tipo_cpte.invoice_type + ' - ' + \
            tipo_cpte.rec_name


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
            'pos': self.start.pos.id,
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
        Pos = pool.get('account.pos')
        PosSequence = pool.get('account.pos.sequence')
        total_amount = Decimal('0')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('invoice_date', '>=', data['from_date']),
            ('invoice_date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', '=', data['pos']),
        ], order=[('number', 'ASC')])

        company = Company(data['company'])
        pos = Pos(data['pos'])
        pos_sequences = PosSequence.search([
            ('pos', '=', pos.id)
        ])
        #for invoice in invoices:
        #    total_amount = invoice.total_amount + total_amount

        report_context = super(SubdiarioSaleTypeReport, cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['pos'] = pos
        report_context['tipos_cptes'] = pos_sequences
        report_context['invoices'] = invoices
        report_context['total_amount'] = total_amount
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_iva'] = cls.get_iva
        report_context['get_account'] = cls.get_account
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iibb_name'] = cls.get_iibb_name
        return report_context

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        return tipo_cpte.invoice_type + ' - ' + \
            tipo_cpte.rec_name

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
            'pos': self.start.pos.id,
            }
        return action, data


class SubdiarioSaleSubdivisionReport(Report, Subdiario):
    __name__ = 'subdiario.sale_subdivision_report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Company = pool.get('company.company')
        Pos = pool.get('account.pos')
        Subdivision = pool.get('country.subdivision')
        total_amount = Decimal('0')

        invoices = Invoice.search([
            ('state', 'in', ['posted', 'paid']),
            ('type', '=', 'out'),
            ('invoice_date', '>=', data['from_date']),
            ('invoice_date', '<=', data['to_date']),
            ('company', '=', data['company']),
            ('pos', '=', data['pos']),
        ], order=[('number', 'ASC')])

        company = Company(data['company'])
        pos = Pos(data['pos'])
        # search subdivisions of Argentina
        subdivisions = Subdivision.search([
            ('country.code', '=', 'AR')
        ], order=[('name', 'ASC')])
        #for invoice in invoices:
        #    total_amount = invoice.total_amount + total_amount

        report_context = super(SubdiarioSaleSubdivisionReport, cls).get_context(records, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']
        report_context['pos'] = pos
        report_context['subdivisions'] = subdivisions
        report_context['invoices'] = invoices
        report_context['total_amount'] = total_amount
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_iva'] = cls.get_iva
        report_context['get_account'] = cls.get_account
        report_context['get_iibb'] = cls.get_iibb
        report_context['get_iibb_name'] = cls.get_iibb_name
        return report_context

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        return tipo_cpte.invoice_type + ' - ' + \
            tipo_cpte.rec_name
