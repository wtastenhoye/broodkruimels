from odoo import models,fields

class procurement_group(models.Model):
    _inherit = 'procurement.group'

    bol_odoo_shipment_id = fields.Many2one('bol.inbound.shipment.ept',string='Shipment')