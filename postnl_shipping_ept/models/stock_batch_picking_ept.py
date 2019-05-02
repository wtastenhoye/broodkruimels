# Copyright (c) 2019 Emipro Technologies Pvt Ltd (www.emiprotechnologies.com). All rights reserved.
from odoo import models, fields, api, _

class PostNLStockPickingBatchEpt(models.Model):
    _inherit = "stock.picking.batch"
    delivery_type_ept = fields.Selection(selection_add=[('postnl_ept', 'PostNL')])

class PostNLStockPickingToBatchEpt(models.TransientModel):
    _inherit = 'stock.picking.to.batch.ept'
    delivery_type_ept = fields.Selection(selection_add=[('postnl_ept', 'PostNL')])