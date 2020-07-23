# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import invoice


def register():
    Pool.register(
        invoice.Invoice,
        invoice.SubdiarioPurchaseStart,
        invoice.SubdiarioSaleStart,
        module='subdiario', type_='model')
    Pool.register(
        invoice.SubdiarioPurchase,
        invoice.SubdiarioSale,
        invoice.SubdiarioSaleType,
        invoice.SubdiarioSaleSubdivision,
        module='subdiario', type_='wizard')
    Pool.register(
        invoice.SubdiarioPurchaseReport,
        invoice.SubdiarioSaleReport,
        invoice.SubdiarioSaleTypeReport,
        invoice.SubdiarioSaleSubdivisionReport,
        module='subdiario', type_='report')
