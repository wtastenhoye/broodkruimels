from odoo import models,fields,api

class stock_warehouse(models.Model):
    _inherit='stock.warehouse'
    
    is_fbb_warehouse=fields.Boolean('Is FBB Warehouse')
    nck_stock_location=fields.Many2one('stock.location',"NCK Stock Location")