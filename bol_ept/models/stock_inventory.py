from odoo import models,fields,api,_

class stock_inventory(models.Model):
    _inherit='stock.inventory'

    bol_instance_id=fields.Many2one('bol.instance.ept',"Instance")
    
    def get_fbb_inventory_ept(self,instance):
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not instance:
            instances=self.env['bol.instance.ept'].search([('state','=','confirmed')])
        else:
            instances=instance
        for instance in instances:
            bol_job=log_book_obj.create({
                    'application':'shipment',
                    'message':'Perform Import LVB Inventory operation',
                    'operation_type':'import',
                    'bol_request':'/services/rest/inventory',
                    'bol_instance_id':instance.id
                })
            plaza_api=instance.connect_in_bol()
            offers=[]
            page=0
            try:
                while True:
                    page=page+1
                    response=[]
                    response=plaza_api.fbb_inventory.getInventory(page=page)
                    if response.Offers:
                        offers=offers+response.Offers
                    else:
                        break
            except Exception as e:
                bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':e,
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
                continue
            bol_job.write({'bol_response':"Total %d products\' stock got in response"%(len(offers))})
            stock_invetory_products=[]
            nck_stock_invetory_products=[]
            for offer in offers:
                ean=offer.EAN
                stock=offer.Stock
                nck_stock=offer.NCK_Stock
                bol_product=self.env['bol.product.ept'].search_product(ean=ean,instance_id=instance.id)
                if not bol_product:
                    bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':"Product with EAN %s is not found"%(ean),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'not_found',
                    'bol_instance_id':instance.id
                    })
                    continue
                if not bol_product.bol_bsku:
                    bol_product.bol_bsku = offer.BSKU
                if stock>0:stock_invetory_products.append({'product_id':bol_product.product_id,'product_qty':stock,"location_id":instance.fbb_warehouse_id.lot_stock_id.id})
                if nck_stock>0:nck_stock_invetory_products.append({'product_id':bol_product.product_id,'product_qty':nck_stock,"location_id":instance.fbb_warehouse_id.nck_stock_location.id})
            sequence=self.env.ref("bol_ept.seq_bol_fbb_inventory_adjustment_ept")
            name=sequence and sequence.next_by_id() or '/'
            fbb_inv=stock_invetory_products and self.env['stock.inventory'].create_stock_inventory(products=stock_invetory_products,location_id=instance.fbb_warehouse_id.lot_stock_id,auto_validate=instance.validate_bol_stock_inventory,name=name)
            fbb_inv and fbb_inv.write({'bol_instance_id':instance.id})
            sequence=self.env.ref("bol_ept.seq_bol_fbb_nck_inventory_adjustment_ept")
            name=sequence and sequence.next_by_id() or '/'
            fbb_nck_inv=nck_stock_invetory_products and self.env['stock.inventory'].create_stock_inventory(products=nck_stock_invetory_products,location_id=instance.fbb_warehouse_id.nck_stock_location,auto_validate=instance.validate_bol_stock_inventory,name=name)
            fbb_nck_inv and fbb_nck_inv.write({'bol_instance_id':instance.id})
        return True
    
    def auto_import_fbb_inventory_ept(self,ctx):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.get_fbb_inventory_ept(instance)
        return True