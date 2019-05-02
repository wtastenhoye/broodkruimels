from odoo import models,api,fields

class account_invoice(models.Model):
    _inherit="account.invoice"
    
    bol_instance_id = fields.Many2one("bol.instance.ept","Instance")
    