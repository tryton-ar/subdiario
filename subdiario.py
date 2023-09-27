# -*- coding: utf8 -*-
# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import stdnum.ar.cuit as cuit
import stdnum.ar.dni as dni
from pysimplesoap.client import SimpleXMLElement
from unidecode import unidecode
from decimal import Decimal
from datetime import date

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction

_ZERO = Decimal('0')


class Subdiario(object):

    @classmethod
    def get_amount(cls, invoice, field):
        value = getattr(invoice, field)
        amount = value
        if invoice.currency != invoice.company.currency:
            amount = cls.get_secondary_amount(invoice, value)
        return amount

    @classmethod
    def get_secondary_amount(cls, invoice, value):
        pool = Pool()
        Currency = pool.get('currency.currency')

        if invoice.pos and invoice.pos.pos_type == 'electronic':
            afip_tr, = [tr for tr in invoice.transactions
                if tr.pyafipws_result == 'A']
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
    def get_exento(cls, lines):
        amount = Decimal('0')
        for line in lines:
            for tax in line.taxes:
                if tax.group.afip_kind == 'exento':
                    amount += line.amount
        return amount

    @classmethod
    def get_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            for tax in line.taxes:
                if tax.group.afip_kind == 'gravado':
                    amount += line.amount
        return amount

    @classmethod
    def get_no_gravado(cls, lines):
        amount = Decimal('0')
        for line in lines:
            for tax in line.taxes:
                if tax.group.afip_kind == 'no_gravado':
                    amount += line.amount
        return amount

    @classmethod
    def get_iva(cls, invoice, rate, group_tax='gravado'):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if (invoice_tax.tax.rate and
                    invoice_tax.tax.rate == Decimal(rate) and
                    invoice_tax.tax.group.afip_kind == 'gravado'):
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_percep_iibb(cls, invoice):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind == 'provincial':
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_percep_iva(cls, invoice):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind == 'nacional':
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_percep_otras(cls, invoice):
        amount = Decimal('0')
        for invoice_tax in invoice.taxes:
            if invoice_tax.tax.group.afip_kind not in (
                    'gravado', 'no_gravado', 'exento',
                    'provincial', 'nacional'):
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_party_tax_identifier(cls, invoice):
        code = ''
        if invoice.party_tax_identifier:
            code = invoice.party_tax_identifier.code
        elif invoice.party.vat_number:
            code = invoice.party.vat_number
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
    def format_ci(cls, iva_condition):
        iva_condition = iva_condition.lower()
        if iva_condition in ('exento', 'monotributo'):
            return iva_condition.upper()[:2]
        if '_' in iva_condition:
            first, second = iva_condition.split('_')
        else:
            first, second = iva_condition.split(' ')
        return '%s%s' % (first[:1].upper(), second[:1].upper())

    @classmethod
    def get_iva_condition(cls, invoice):
        return cls.format_ci(invoice.party_iva_condition or
            invoice.party.iva_condition)

    @classmethod
    def format_tipo_comprobante(cls, tipo_cpte):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        return '%s - %s' % (tipo_cpte,
            dict(Invoice._fields['tipo_comprobante'].selection)[tipo_cpte])

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
    def get_concepto(cls, lines):
        amounts = [(c.amount, c.description) for c in lines]
        concepto_amount = Decimal('0')
        concepto = ''
        for amount, description in amounts:
            if amount >= concepto_amount:
                amount = concepto_amount
                concepto = description
        return concepto

    @classmethod
    def get_sum_neto_by_tax(cls, tax, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
                base_amount = invoice_tax.base
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, base_amount)
                else:
                    amount += invoice.currency.round(base_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax(cls, tax, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
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
            party_iva_condition = (invoice.party_iva_condition or
                invoice.party.iva_condition)
            if party_iva_condition != iva_condition:
                continue
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
            party_iva_condition = (invoice.party_iva_condition or
                invoice.party.iva_condition)
            if party_iva_condition != iva_condition:
                continue
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax.group.afip_kind != 'gravado':
                    continue
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition or
                invoice.party.iva_condition)
            if party_iva_condition != iva_condition:
                continue
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
                base_amount = invoice_tax.base
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, base_amount)
                else:
                    amount += invoice.currency.round(base_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_iva_condition(cls, tax, iva_condition,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            party_iva_condition = (invoice.party_iva_condition or
                invoice.party.iva_condition)
            if party_iva_condition != iva_condition:
                continue
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount

    @classmethod
    def get_sum_neto_by_tax_and_subdivision(cls, tax, subdivision, invoices):
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision != subdivision:
                continue
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
                base_amount = invoice_tax.base
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, base_amount)
                else:
                    amount += invoice.currency.round(base_amount)
        return amount

    @classmethod
    def get_sum_percibido_by_tax_and_subdivision(cls, tax, subdivision,
            invoices):
        amount = Decimal('0')
        for invoice in invoices:
            if invoice.invoice_address.subdivision != subdivision:
                continue
            for invoice_tax in invoice.taxes:
                if invoice_tax.tax != tax:
                    continue
                tax_amount = invoice_tax.amount
                if invoice.currency != invoice.company.currency:
                    amount += cls.get_secondary_amount(invoice, tax_amount)
                else:
                    amount += invoice.currency.round(tax_amount)
        return amount


class SubdiarioPurchaseStart(ModelView):
    'Subdiario de Compras'
    __name__ = 'subdiario.purchase.start'

    date = fields.Selection([
        ('date', 'Effective Date'),
        ('post_date', 'Post Date'),
        ], 'Use', required=True)
    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)

    @staticmethod
    def default_date():
        return 'post_date'

    @staticmethod
    def default_from_date():
        Date = Pool().get('ir.date')
        return date(Date.today().year, 1, 1)

    @staticmethod
    def default_to_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


class SubdiarioPurchase(Wizard):
    'Subdiario de Compras'
    __name__ = 'subdiario.purchase'

    start = StateView('subdiario.purchase.start',
        'subdiario.purchase_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print Spreadsheet', 'print_', 'tryton-print', True),
            Button('Print PDF', 'print_pdf', 'tryton-print'),
            ])
    print_ = StateReport('subdiario.purchase_report')
    print_pdf = StateReport('subdiario.purchase_report_pdf')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'date': self.start.date,
            }
        return action, data

    def do_print_pdf(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'date': self.start.date,
            }
        return action, data


class SubdiarioPurchaseReport(Report, Subdiario):
    'Subdiario de Compras'
    __name__ = 'subdiario.purchase_report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        Tax = pool.get('account.tax')
        Subdivision = pool.get('country.subdivision')

        total_op_exentas = _ZERO
        total_neto_gravado = _ZERO
        total_conc_no_gravados = _ZERO
        total_iva_21 = _ZERO
        total_iva_105 = _ZERO
        total_iva_27 = _ZERO
        total_percep_iibb = _ZERO
        total_percep_iva = _ZERO
        total_percep_otras = _ZERO
        total_total = _ZERO

        company = Company(data['company'])

        clause = [
            ('company', '=', data['company']),
            ('type', '=', 'in'),
            ('state', 'in', ['posted', 'paid']),
            ]
        if data['date'] == 'post_date':
            clause.extend([
                ('move.post_date', '>=', data['from_date']),
                ('move.post_date', '<=', data['to_date']),
                ])
        else:  # data['date'] == 'date':
            clause.extend([
                ('move.date', '>=', data['from_date']),
                ('move.date', '<=', data['to_date']),
                ])

        invoices = Invoice.search(clause, order=[('invoice_date', 'ASC')])

        taxes = Tax.search([
            ('group.kind', 'in', ['purchase', 'both']),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        alicuotas = Tax.search([
            ('group.kind', '=', 'purchase'),
            ('group.afip_kind', 'in', ['gravado', 'no_gravado', 'exento']),
            ], order=[('name', 'ASC')])

        iibb_taxes = Tax.search([
            ('group.kind', 'in', ['purchase', 'both']),
            ('group.afip_kind', '=', 'provincial'),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        subdivisions = Subdivision.search([
            ('country.code', '=', 'AR')
            ], order=[('name', 'ASC')])

        iva_conditions = [
            'responsable_inscripto',
            'exento',
            'consumidor_final',
            'monotributo',
            'no_alcanzado',
            ]

        for invoice in invoices:
            total_op_exentas += cls.get_exento(invoice.lines)
            total_neto_gravado += cls.get_gravado(invoice.lines)
            total_conc_no_gravados += cls.get_no_gravado(invoice.lines)
            total_iva_21 += cls.get_iva(invoice, '0.21')
            total_iva_105 += cls.get_iva(invoice, '0.105')
            total_iva_27 += cls.get_iva(invoice, '0.27')
            total_percep_iibb += cls.get_percep_iibb(invoice)
            total_percep_iva += cls.get_percep_iva(invoice)
            total_percep_otras += cls.get_percep_otras(invoice)
            total_total += cls.get_amount(invoice, 'total_amount')

        report_context = super().get_context(records, header, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']

        # objects
        report_context['invoices'] = invoices
        report_context['taxes'] = taxes
        report_context['alicuotas'] = alicuotas
        report_context['iibb_taxes'] = iibb_taxes
        report_context['subdivisions'] = subdivisions
        report_context['iva_conditions'] = iva_conditions

        # amount columns
        report_context['get_exento'] = cls.get_exento
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_percep_iibb'] = cls.get_percep_iibb
        report_context['get_percep_iva'] = cls.get_percep_iva
        report_context['get_percep_otras'] = cls.get_percep_otras
        report_context['get_amount'] = cls.get_amount

        # other columns
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['format_ci'] = cls.format_ci
        report_context['format_tipo_comprobante'] = cls.format_tipo_comprobante
        report_context['get_iibb_name'] = cls.get_iibb_name
        report_context['get_zona_iibb'] = cls.get_zona_iibb
        report_context['get_account'] = cls.get_account
        report_context['get_concepto'] = cls.get_concepto

        # total amounts
        report_context['total_op_exentas'] = total_op_exentas
        report_context['total_neto_gravado'] = total_neto_gravado
        report_context['total_conc_no_gravados'] = total_conc_no_gravados
        report_context['total_iva_21'] = total_iva_21
        report_context['total_iva_105'] = total_iva_105
        report_context['total_iva_27'] = total_iva_27
        report_context['total_percep_iibb'] = total_percep_iibb
        report_context['total_percep_iva'] = total_percep_iva
        report_context['total_percep_otras'] = total_percep_otras
        report_context['total_total'] = total_total

        # methods for grouping data
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
        report_context['get_sum_neto_by_tax_and_subdivision'] = (
            cls.get_sum_neto_by_tax_and_subdivision)
        report_context['get_sum_percibido_by_tax_and_subdivision'] = (
            cls.get_sum_percibido_by_tax_and_subdivision)
        return report_context


class SubdiarioPurchasePDFReport(SubdiarioPurchaseReport):
    'Subdiario de Compras'
    __name__ = 'subdiario.purchase_report_pdf'


class SubdiarioSaleStart(ModelView):
    'Subdiario de Ventas'
    __name__ = 'subdiario.sale.start'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    pos = fields.Many2Many('account.pos', None, None, 'Points of Sale',
        required=True, help="Por defecto puntos de venta electronicos")

    @staticmethod
    def default_from_date():
        Date = Pool().get('ir.date')
        return date(Date.today().year, 1, 1)

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
    'Subdiario de Ventas'
    __name__ = 'subdiario.sale'

    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print Spreadsheet', 'print_', 'tryton-print', True),
            Button('Print PDF', 'print_pdf', 'tryton-print'),
            ])
    print_ = StateReport('subdiario.sale_report')
    print_pdf = StateReport('subdiario.sale_report_pdf')

    def do_print_(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'pos': [p.id for p in self.start.pos],
            }
        return action, data

    def do_print_pdf(self, action):
        data = {
            'company': self.start.company.id,
            'from_date': self.start.from_date,
            'to_date': self.start.to_date,
            'pos': [p.id for p in self.start.pos],
            }
        return action, data


class SubdiarioSaleReport(Report, Subdiario):
    'Subdiario de Ventas'
    __name__ = 'subdiario.sale_report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        Tax = pool.get('account.tax')

        total_op_exentas = _ZERO
        total_neto_gravado = _ZERO
        total_conc_no_gravados = _ZERO
        total_iva_21 = _ZERO
        total_iva_105 = _ZERO
        total_iva_27 = _ZERO
        total_percep_iibb = _ZERO
        total_percep_iva = _ZERO
        total_percep_otras = _ZERO
        total_total = _ZERO

        company = Company(data['company'])

        clause = [
            ('company', '=', data['company']),
            ('type', '=', 'out'),
            ['OR', ('state', 'in', ['posted', 'paid']),
                [('state', '=', 'cancelled'), ('number', '!=', None)]],
            ('pos', 'in', data['pos']),
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ]
        invoices = Invoice.search(clause, order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        taxes = Tax.search([
            ('group.kind', 'in', ['sale', 'both']),
            ('active', 'in', [True, False]),
            ], order=[('name', 'ASC')])

        alicuotas = Tax.search([
            ('group.kind', '=', 'sale'),
            ('group.afip_kind', 'in', ['gravado', 'no_gravado', 'exento']),
            ], order=[('name', 'ASC')])

        iva_conditions = [
            'responsable_inscripto',
            'exento',
            'consumidor_final',
            'monotributo',
            'no_alcanzado',
            ]

        for invoice in invoices:
            total_op_exentas += cls.get_exento(invoice.lines)
            total_neto_gravado += cls.get_gravado(invoice.lines)
            total_conc_no_gravados += cls.get_no_gravado(invoice.lines)
            total_iva_21 += cls.get_iva(invoice, '0.21')
            total_iva_105 += cls.get_iva(invoice, '0.105')
            total_iva_27 += cls.get_iva(invoice, '0.27')
            total_percep_iibb += cls.get_percep_iibb(invoice)
            total_percep_iva += cls.get_percep_iva(invoice)
            total_percep_otras += cls.get_percep_otras(invoice)
            total_total += cls.get_amount(invoice, 'total_amount')

        report_context = super().get_context(records, header, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']

        # objects
        report_context['invoices'] = invoices
        report_context['taxes'] = taxes
        report_context['alicuotas'] = alicuotas
        report_context['iva_conditions'] = iva_conditions

        # amount columns
        report_context['get_exento'] = cls.get_exento
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_percep_iibb'] = cls.get_percep_iibb
        report_context['get_percep_iva'] = cls.get_percep_iva
        report_context['get_percep_otras'] = cls.get_percep_otras
        report_context['get_amount'] = cls.get_amount

        # other columns
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['format_ci'] = cls.format_ci
        report_context['get_iva_condition'] = cls.get_iva_condition
        report_context['get_iibb_name'] = cls.get_iibb_name
        report_context['get_zona_iibb'] = cls.get_zona_iibb
        report_context['get_account'] = cls.get_account

        # total amounts
        report_context['total_op_exentas'] = total_op_exentas
        report_context['total_neto_gravado'] = total_neto_gravado
        report_context['total_conc_no_gravados'] = total_conc_no_gravados
        report_context['total_iva_21'] = total_iva_21
        report_context['total_iva_105'] = total_iva_105
        report_context['total_iva_27'] = total_iva_27
        report_context['total_percep_iibb'] = total_percep_iibb
        report_context['total_percep_iva'] = total_percep_iva
        report_context['total_percep_otras'] = total_percep_otras
        report_context['total_total'] = total_total

        # methods for grouping data
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


class SubdiarioSalePDFReport(SubdiarioSaleReport):
    'Subdiario de Ventas'
    __name__ = 'subdiario.sale_report_pdf'


class SubdiarioSaleType(Wizard):
    'Subdiario de Ventas por tipo de comprobante'
    __name__ = 'subdiario.sale.type'

    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print Spreadsheet', 'print_', 'tryton-print', True),
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
    'Subdiario de Ventas por tipo de comprobante'
    __name__ = 'subdiario.sale_type_report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        PosSequence = pool.get('account.pos.sequence')

        company = Company(data['company'])

        invoices = Invoice.search([
            ('company', '=', data['company']),
            ('type', '=', 'out'),
            ('pos', 'in', data['pos']),
            ['OR', ('state', 'in', ['posted', 'paid']),
                [('state', '=', 'cancelled'), ('number', '!=', None)]],
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ], order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        pos_sequences = PosSequence.search([
            ('pos', 'in', data['pos'])
            ])

        report_context = super().get_context(records, header, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']

        # objects
        report_context['invoices'] = invoices
        report_context['tipos_cptes'] = pos_sequences

        # amount columns
        report_context['get_exento'] = cls.get_exento
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_percep_iibb'] = cls.get_percep_iibb
        report_context['get_percep_iva'] = cls.get_percep_iva
        report_context['get_percep_otras'] = cls.get_percep_otras
        report_context['get_amount'] = cls.get_amount

        # other columns
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['format_ci'] = cls.format_ci
        report_context['get_iva_condition'] = cls.get_iva_condition
        return report_context


class SubdiarioSaleSubdivision(Wizard):
    'Subdiario de Ventas por jurisdicción'
    __name__ = 'subdiario.sale.subdivision'

    start = StateView('subdiario.sale.start',
        'subdiario.sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print Spreadsheet', 'print_', 'tryton-print', True),
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
    'Subdiario de Ventas por jurisdicción'
    __name__ = 'subdiario.sale_subdivision_report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        Subdivision = pool.get('country.subdivision')

        company = Company(data['company'])

        invoices = Invoice.search([
            ('company', '=', data['company']),
            ('type', '=', 'out'),
            ('pos', 'in', data['pos']),
            ['OR', ('state', 'in', ['posted', 'paid']),
                [('state', '=', 'cancelled'), ('number', '!=', None)]],
            ('move.date', '>=', data['from_date']),
            ('move.date', '<=', data['to_date']),
            ], order=[
            ('pos', 'ASC'),
            ('invoice_date', 'ASC'),
            ('invoice_type', 'ASC'),
            ('number', 'ASC'),
            ])

        subdivisions = Subdivision.search([
            ('country.code', '=', 'AR')
            ], order=[('name', 'ASC')])

        report_context = super().get_context(records, header, data)
        report_context['company'] = company
        report_context['from_date'] = data['from_date']
        report_context['to_date'] = data['to_date']

        # objects
        report_context['invoices'] = invoices
        report_context['subdivisions'] = subdivisions

        # amount columns
        report_context['get_exento'] = cls.get_exento
        report_context['get_gravado'] = cls.get_gravado
        report_context['get_no_gravado'] = cls.get_no_gravado
        report_context['get_iva'] = cls.get_iva
        report_context['get_percep_iibb'] = cls.get_percep_iibb
        report_context['get_percep_iva'] = cls.get_percep_iva
        report_context['get_percep_otras'] = cls.get_percep_otras
        report_context['get_amount'] = cls.get_amount

        # other columns
        report_context['get_party_tax_identifier'] = (
            cls.get_party_tax_identifier)
        report_context['format_ci'] = cls.format_ci
        report_context['get_iva_condition'] = cls.get_iva_condition
        return report_context
