from odoo import models,fields,api,_
from odoo.exceptions import Warning

class bol_process_import_export(models.TransientModel):
    _name='bol.process.import.export'
    
    instance_ids = fields.Many2many("bol.instance.ept",'bol_instance_import_export_rel','process_id','bol_instance_id',"Instances")
    publish=fields.Boolean("Publish In Website",default=False)
    is_export_products=fields.Boolean("Export/Update Products",help="Export Products that are prepared for bol Export or Update product in bol.com.")    
    sync_product_from_bol=fields.Boolean("Sync Products")
    is_update_products=fields.Boolean("Update Products",help="Update product details of products that are already exported.")
    is_fbr_import_orders=fields.Boolean("Import FBR Orders")
    is_fbb_import_orders=fields.Boolean("Import FBB Orders")
    is_update_order_status=fields.Boolean("Update Order Status",help="Update order status in Bol if it is changed in Odoo.")
    sync_price_with_product=fields.Boolean("Sync Product Price?",help="Check if you want to import price along with products",default=False)
    is_import_stock=fields.Boolean("Import Stock",default=False)
    is_import_trasport=fields.Boolean("Import Transport",default=False)
    is_import_delivery_window=fields.Boolean("Import Delivery Window",default=False)
    product_ean=fields.Char("EAN")
    fullfillment_by=fields.Selection([('FBR','FBR'),('FBB','FBB')],'Fullfillment By',default='FBR')
    is_retrive_product_status=fields.Boolean("Get product status")
    is_import_shipment_details=fields.Boolean("Import Shipments")
    is_retrive_shipment_status=fields.Boolean("Get Shipment Statuses")
    is_import_invetory=fields.Boolean("Import LVB/FBB Inventory")
    is_import_return_request=fields.Boolean("Import Return Requests")
        
    @api.model
    def default_get(self,fields):
        res = super(bol_process_import_export,self).default_get(fields)
        if 'default_instance_id' in self._context:
            res.update({'instance_ids':[(6,0,[self._context.get('default_instance_id')])]})
        elif 'instance_ids' in fields:
            instances = self.env['bol.instance.ept'].search([('state','=','confirmed')])
            res.update({'instance_ids':[(6,0,instances.ids)]})
        return res
    
    @api.multi
    def execute(self):                                          
        if self.is_export_products:
            self.export_products()
        if self.sync_product_from_bol:
            self.sync_products()
        if self.is_import_trasport:
            self.import_transport()
        if self.is_import_delivery_window:
            self.import_delivery_window()
        if self.is_retrive_product_status:
            self.retrive_product_status()
        if self.is_fbr_import_orders:
            self.import_sale_orders(fullfillment_by='fbr')
        if self.is_fbb_import_orders:
            self.import_sale_orders(fullfillment_by='fbb')
        if self.is_import_shipment_details:
            self.import_shipments()
        if self.is_update_order_status:
            self.update_order_status()
        if self.is_retrive_shipment_status:
            self.retrive_shipment_status()
        if self.is_import_invetory:
            self.import_invetory()
        if self.is_import_return_request:
            self.import_return_request()
        return True
    
    @api.multi
    def sync_products(self):
        bol_template_obj=self.env['bol.product.ept']
        for instance in self.instance_ids:
            bol_template_obj.sync_product(instance,ean=self.product_ean,update_price=instance.sync_price_with_product)
        return True
        
    @api.multi
    def sync_selective_products(self):
        active_ids=self._context.get('active_ids')
        bol_product_obj=self.env['bol.product.ept']        
        bol_products=bol_product_obj.search([('id','in',active_ids),('exported_in_bol','=',True)])
        if not bol_products:
            raise Warning("You can only sync already exported products")
        for bol_product in bol_products:
            bol_product_obj.sync_product(instance=bol_product.bol_instance_id,ean=bol_product.ean,update_price=self.sync_price_with_product)
        return True
    
    @api.multi
    def import_transport(self):
        fbb_transport_obj=self.env['bol.fbb.transport.ept']
        for instance in self.instance_ids:
            fbb_transport_obj.import_transport(instance)
    
    @api.multi
    def import_delivery_window(self):
        delivery_window_obj=self.env['bol.delivery.window.ept']
        for instance in self.instance_ids:
            delivery_window_obj.import_delivery_window(instance)        
    
    @api.multi
    def prepare_product_for_export_in_bol(self):
        bol_product_obj=self.env['bol.product.ept']
        ids=self._context.get('active_ids',[])
        is_product_template=self._context.get('product_template',False)
        is_product_product=self._context.get('product_product',False)
        odoo_products=[]
        if is_product_template:
            odoo_templates=self.env['product.template'].search([('id','in',ids)])
            for odoo_template in odoo_templates:
                for odoo_product in odoo_template.product_variant_ids:
                    odoo_product.barcode and odoo_products.append(odoo_product)
        if is_product_product:
            odoo_products=self.env['product.product'].search([('id','in',ids),('barcode','!=',False)])
        if not odoo_products:
            raise Warning("Barcode (EAN) not set in selected products")
        for instance in self.instance_ids:
            for odoo_product in odoo_products:
                bol_product=bol_product_obj.search([('bol_instance_id','=',instance.id),('product_id','=',odoo_product.id)])                
                if not bol_product:
                    bol_product_obj.create({'bol_instance_id':instance.id,'product_id':odoo_product.id,'name':odoo_product.name,'product_description':odoo_product.product_tmpl_id.description_sale,'fullfillment_method':self.fullfillment_by,'ean':odoo_product.barcode,'reference_code':odoo_product.default_code,'condition':instance.default_codition,'delivery_code':instance.default_delivery_code,'publish':instance.is_publish})
        return True
    
    @api.multi
    def export_products(self):
        instance_settings = {}
        config_settings = {}
        is_publish = False
        bol_product_obj=self.env['bol.product.ept']
        if self._context.get('process')=='export_selective_products':
            bol_product_ids=self._context.get('active_ids')
            instances = self.env['bol.instance.ept'].search([('state','=','confirmed')])
        else:            
            bol_product_ids=[]
            instances=self.instance_ids
            for instance in instances:
                instance_settings.update({"instance_id":instance})
                if instance.is_publish:
                    config_settings.update({"is_publish":True})
                instance_settings.update({"settings":config_settings})        
        
        for instance in instances:
            if instance_settings:
                setting = instance_settings.get('settings')
                is_publish = setting.get('is_publish')
            else:
                is_publish = self.publish
                                
            if bol_product_ids:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id),('id','in',bol_product_ids)])
            else:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id)])
                
            bol_products and bol_product_obj.export_products_in_bol(instance,bol_products,is_publish)
        return True
    
    @api.multi
    def delete_products(self):
        bol_product_obj=self.env['bol.product.ept']
        if self._context.get('process')=='delete_products':
            bol_product_ids=self._context.get('active_ids')
            instances = self.env['bol.instance.ept'].search([('state','=','confirmed')])
        else:            
            instances=self.instance_ids
        
        for instance in instances:
            if bol_product_ids:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id),('id','in',bol_product_ids)])
            else:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id),('exported_in_bol','=',True)])
                
            bol_products and bol_product_obj.delete_products_in_bol(instance,bol_products)
        return True
    
    @api.multi
    def retrive_product_status(self):
        bol_product_obj=self.env['bol.product.ept']
        if self._context.get('process')=='retrive_product_status':
            bol_product_ids=self._context.get('active_ids')
            instances = self.env['bol.instance.ept'].search([('state','=','confirmed')])
        else:            
            bol_product_ids=[]
            instances=self.instance_ids
        
        for instance in instances:
            if bol_product_ids:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id),('id','in',bol_product_ids)])
            else:
                bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id),('exported_in_bol','=',True),('published','=',False)])
                
            bol_products and bol_product_obj.retrive_product_status(instance,bol_products)
        return True
    
    @api.multi
    def retrive_shipment_status(self):
        self.env['stock.picking'].get_process_status(instance=self.instance_ids)
        return True
    
    @api.multi
    def import_sale_orders(self,fullfillment_by='fbr'):
        sale_order_obj=self.env['sale.order']
        for instance in self.instance_ids:
            sale_order_obj.import_bol_orders(instance,fullfillment_by=fullfillment_by)
        return True
    
    @api.multi
    def import_return_request(self):
        return_handle_obj=self.env['return.handle.ept']
        for instance in self.instance_ids:
            return_handle_obj.import_return_requests(instance)
        return True
    
    @api.multi
    def import_shipments(self,shipment_fullfillment_by='fbb'):
        stock_picking_obj=self.env['stock.picking']
        for instance in self.instance_ids:
            stock_picking_obj.import_shipments(instance,shipment_fullfillment_by=instance.import_shipment_order_type)
        return True
    
    @api.multi
    def update_order_status(self):
        sale_order_obj=self.env['sale.order']
        for instance in self.instance_ids:
            sale_order_obj.update_bol_order_status(instance)
        return True
    
    @api.multi
    def import_invetory(self):
        self.env['stock.inventory'].get_fbb_inventory_ept(instance=self.instance_ids)
        return True