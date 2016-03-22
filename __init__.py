# This file is part of the subdiario module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *
from .subdiario import *


def register():
    Pool.register(
        Invoice,
        SubdiarioPurchaseStart,
        SubdiarioSaleStart,
        module='subdiario', type_='model')
    Pool.register(
        SubdiarioPurchase,
        SubdiarioSale,
        SubdiarioSaleType,
        SubdiarioSaleSubdivision,
        module='subdiario', type_='wizard')
    Pool.register(
        SubdiarioPurchaseReport,
        SubdiarioSaleReport,
        SubdiarioSaleTypeReport,
        SubdiarioSaleSubdivisionReport,
        module='subdiario', type_='report')
