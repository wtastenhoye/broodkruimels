from odoo import models,fields,api

class res_partner(models.Model):
    _inherit='res.partner'
    
    house_no=fields.Char("House Number")
    house_no_ext=fields.Char("House Number Extended")
    bol_company_name=fields.Char("Bol Company Name")
    is_bol_customer=fields.Boolean("Is Bol Customer")