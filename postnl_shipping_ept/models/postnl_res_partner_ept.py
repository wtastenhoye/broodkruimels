# Copyright (c) 2019 Emipro Technologies Pvt Ltd (www.emiprotechnologies.com). All rights reserved.
from odoo import models,fields

class ResPartnerEpt(models.Model):
    _inherit="res.partner"
    
    postnl_iban_number=fields.Char("IBAN Number",help="IBAN bank account number, mandatory for COD shipments. Dutch IBAN numbers are 18 characters")


