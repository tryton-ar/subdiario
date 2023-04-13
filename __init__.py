# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import invoice
from . import subdiario


def register():
    Pool.register(
        invoice.Invoice,
        subdiario.SubdiarioPurchaseStart,
        subdiario.SubdiarioSaleStart,
        module='subdiario', type_='model')
    Pool.register(
        subdiario.SubdiarioPurchase,
        subdiario.SubdiarioSale,
        subdiario.SubdiarioSaleType,
        subdiario.SubdiarioSaleSubdivision,
        module='subdiario', type_='wizard')
    Pool.register(
        subdiario.SubdiarioPurchaseReport,
        subdiario.SubdiarioPurchasePDFReport,
        subdiario.SubdiarioSaleReport,
        subdiario.SubdiarioSalePDFReport,
        subdiario.SubdiarioSaleTypeReport,
        subdiario.SubdiarioSaleSubdivisionReport,
        module='subdiario', type_='report')
