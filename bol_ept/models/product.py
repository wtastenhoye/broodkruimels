from odoo import models,fields,api

class product_product(models.Model):
    _inherit= 'product.product'
    
    @api.multi
    def _bol_product_count(self):
        bol_product_obj = self.env['bol.product.ept']
        for product in self:
            bol_products=bol_product_obj.search([('product_id','=',product.id)])
            product.bol_product_count = len(bol_products) if bol_products else 0
                           
    bol_product_count = fields.Integer(string='# Sales',compute='_bol_product_count')
    
class product_template(models.Model):
    _inherit= 'product.template'
    
    @api.multi
    def _bol_template_count(self):
        bol_product_template_obj = self.env['bol.product.ept']
        for template in self:
            bol_templates=bol_product_template_obj.search([('product_id.product_tmpl_id','=',template.id)])
            template.bol_product_count = len(bol_templates) if bol_templates else 0
                           
    bol_product_count = fields.Integer(string='# Sales',compute='_bol_template_count')    