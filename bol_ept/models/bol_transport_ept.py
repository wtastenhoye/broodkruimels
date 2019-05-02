from odoo import models,fields,api,_

class bol_fbb_transport_ept(models.Model):
    _name='bol.fbr.transport.ept'
    
    name=fields.Char('Name')
    code=fields.Char('Code')
    carrier_id=fields.Many2one('delivery.carrier',"Delivery Method")