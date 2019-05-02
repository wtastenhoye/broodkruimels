from odoo import models,fields,api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from datetime import datetime,timedelta

class sale_order(models.Model):
    _inherit="sale.order"
    
    @api.multi
    def _prepare_invoice(self):
        """We need to Inherit this method to set Bol instance id in Invoice"""
        res = super(sale_order,self)._prepare_invoice()
        bol_order=self.env['sale.order'].search([('id','=',self.id),('bol_instance_id','!=',False)])
        bol_order and res.update({'bol_instance_id' : bol_order.bol_instance_id and bol_order.bol_instance_id.id or False})
        return res
    
    @api.one
    def _get_bol_order_status(self):
        for order in self:
            flag=False
            for picking in order.picking_ids:
                if picking.state!='cancel':
                    flag=True
                    break   
            if not flag:
                continue
            if order.picking_ids:
                order.updated_in_bol=True
            else:
                order.updated_in_bol=False
            for picking in order.picking_ids:
                if picking.state =='cancel':
                    continue
                if picking.picking_type_id.code!='outgoing':
                    continue
                if not picking.updated_in_bol:
                    order.updated_in_bol=False
                    break

    def _search_bol_order_ids(self,operator,value):
        query="""select sale_order.id from stock_picking
                inner join sale_order on sale_order.procurement_group_id=stock_picking.group_id                    
                inner join stock_picking_type on stock_picking.picking_type_id=stock_picking_type.id
                inner join stock_location on stock_location.id=stock_picking_type.default_location_dest_id and stock_location.usage='customer'
                where stock_picking.updated_in_bol=False and stock_picking.state in ('done','assigned')"""
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids=[]
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id','in',order_ids)]
    
    @api.multi
    def calculate_transaction_fees(self):
        for order in self:
            total_fee=0
            for line in order.order_line:
                total_fee+=line.bol_transaction_fee
            order.total_transaction_fee=total_fee
    
    fullfillment_method=fields.Selection([('FBR','FBR'),('FBB','FBB')],'Fullfillment Method',readonly=True)
    bol_order_number=fields.Char("Order Number",help="Bol Order Number")
    bol_order_id=fields.Char("Order ID",help="Bol Order ID")
    auto_workflow_process_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow")           
    updated_in_bol=fields.Boolean("Updated In Bol",compute='_get_bol_order_status',search='_search_bol_order_ids')
    bol_instance_id=fields.Many2one("bol.instance.ept","Instance")
    total_transaction_fee=fields.Float("Total Transaction Fees",compute=calculate_transaction_fees)
    
    @api.multi
    def create_or_update_bol_customer(self,vals,is_company=False,parent_id=False,type=False,instance=False):
        first_name=vals.Firstname
        last_name=vals.Surname
        if not first_name and not last_name:
            return False
        
        city=vals.City
        name = "%s %s"%(first_name,last_name)
        company_name=hasattr(vals, 'Company') and vals.Company or ''
        if company_name:
            is_company=True
        email=vals.Email                      
        zip=vals.ZipCode            
        address1=vals.Streetname
        house_no=hasattr(vals, 'Housenumber') and vals.Housenumber or ''
        house_no_ext=hasattr(vals, 'HousenumberExtended') and vals.HousenumberExtended or ''
        phone=hasattr(vals, 'DeliveryPhoneNumber') and vals.DeliveryPhoneNumber or ''
        country_name=vals.CountryCode
        
        vals={'name':name,'street':address1,'city':city,
            'country_code':country_name,'country_name':country_name,
            'email_id':email,'postal-code':zip, 'phone':phone,'parent_id':parent_id
            }
        partner=self.env['res.partner'].create_or_update_partner(vals,type)
        partner.write({'house_no':house_no,'house_no_ext':house_no_ext,'is_company':is_company,'is_bol_customer':True})
        return partner  
    
    @api.model
    def check_bol_mismatch_details(self,lines,instance,order_number,bol_job):
        odoo_product_obj=self.env['product.product']
        bol_product_obj=self.env['bol.product.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        mismatch=False
        for line in lines:
            product_ean=line.EAN or False
            product_condition=line.OfferCondition
            odoo_product=False
            if product_ean:
                bol_product=bol_product_obj.search([('ean','=',product_ean),('condition','=',product_condition),('bol_instance_id','=',instance.id)],limit=1)                
                if bol_product:
                    continue
            
            if not odoo_product and not bol_product:
                odoo_product=product_ean and product_condition and odoo_product_obj.search([('barcode','=',product_ean)],limit=1)
            
            if not odoo_product and product_ean:
                bol_product_obj.sync_product(instance,ean=product_ean,update_price=instance.sync_price_with_product)
                odoo_product = odoo_product_obj.search([('barcode','=',product_ean)],limit=1)
                
            if not bol_product and not odoo_product:
                message="Product with %s EAN Not found for order %s"%(product_ean,order_number)
                bol_job_log_obj.create({
                        'job_id':bol_job.id,
                        'message':message,
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'not_found',
                        'bol_instance_id':instance.id
                    })
                mismatch=message
                break
        return mismatch
    
    @api.model
    def get_order_vals(self,result,fullfillment_method,workflow,invoice_address,instance,partner,shipping_address,pricelist_id,payment_term):
        bol_order_number = result.OrderId
                   
        if instance.bol_order_prefix:
            name="%s%s"%(instance.bol_order_prefix,bol_order_number)
        else:
            name=bol_order_number
        
        order_seq=1
        while self.search([('name','=',name)]):
            name=name+"_%s"%(order_seq)
            order_seq+=1

        ordervals = {
            'name' :name,                
            'partner_invoice_id' : invoice_address.ids[0],
            'date_order' :hasattr(result,"DateTimeCustomer") and result.DateTimeCustomer.astimezone() or datetime.now(),
            'warehouse_id' : instance.fbb_warehouse_id.id if fullfillment_method.upper()=='FBB' else instance.fbr_warehouse_id.id,
            'partner_id' : partner.ids[0],
            'partner_shipping_id' : shipping_address.ids[0],
            'state' : 'draft',
            'pricelist_id' : pricelist_id or instance.pricelist_id.id or False,
            'payment_term_id':payment_term or instance.payment_term_id.id or False, 
            'bol_team_id':instance.bol_team_id and instance.bol_team_id.id or False,
            'company_id':instance.company_id.id,
            'client_order_ref':result.OrderId,
        }   
        
        if workflow:
            if not workflow.picking_policy:
                raise Warning("Please configure Sale Auto Workflow properly.")
            ordervals.update({
                'picking_policy' : workflow.picking_policy,
                'invoice_policy':workflow.invoice_policy
                })
        return ordervals
    
    @api.multi
    def import_bol_orders(self,instance=False,fullfillment_by='FBR'):
        instances=[]
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not instance:
            instances=self.env['bol.instance.ept'].search(['|',('fbb_order_auto_import','=',True),('fbr_order_auto_import','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            orders=[]
            page=0
            plaza_api=instance.connect_in_bol()
            bol_job=log_book_obj.create({
                    'application':'order',
                    'message':'Perform Import order operation',
                    'operation_type':'import',
                    'bol_request':'/services/rest/orders/v2',
                    'bol_instance_id':instance.id
                })
            try:
                while True:
                    page=page+1
                    response=[]
                    response=plaza_api.orders.list(params={'fulfilment-method':fullfillment_by, 'page':page})
                    if response:
                        orders=orders+response
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
                return True
            bol_job.write({'bol_response':orders})
            
            import_order_ids=[]
            
            for order in orders:
                if self.search([('bol_instance_id','=',instance.id),('bol_order_id','=',order.OrderId),('fullfillment_method','=ilike',fullfillment_by)]):
                    continue
                lines=order.OrderItems
                if self.check_bol_mismatch_details(lines,instance,order.OrderId,bol_job):
                    continue
                
                workflow=False
                if fullfillment_by=="fbb":
                    workflow=instance.fbb_order_workflow
                else:
                    workflow=instance.fbr_order_workflow
                if not workflow:
                    message="Workflow Configuration not found for this order %s"%(order.OrderId)
                    bol_job_log_obj.create({
                        'job_id':bol_job.id,
                        'message':message,
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'not_found',
                        'bol_instance_id':instance.id
                    })                    
                    continue
                partner=order.CustomerDetails.BillingDetails and self.create_or_update_bol_customer(order.CustomerDetails.BillingDetails, False, False,False,instance)
                if not partner:                    
                    message="Customer Not Available In %s Order"%(order.OrderId)
                    bol_job_log_obj.create({
                        'job_id':bol_job.id,
                        'message':message,
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'not_found',
                        'bol_instance_id':instance.id
                    })
                    continue
                shipping_address=order.CustomerDetails.ShipmentDetails and self.create_or_update_bol_customer(order.CustomerDetails.ShipmentDetails, False,partner.id,'delivery',instance) or partner
                
                bol_order_vals=self.get_order_vals(order, fullfillment_by, workflow, partner, instance, partner, shipping_address, instance.pricelist_id.id, instance.payment_term_id.id)
                order_vals=self.create_sales_order_vals_ept(bol_order_vals)
                order_vals.update({'bol_order_id':order.OrderId,
                                        'bol_order_number':order.OrderId,
                                        'bol_instance_id':instance.id,
                                        'fullfillment_method':fullfillment_by.upper(),
                                        'auto_workflow_process_id':workflow.id,
                                        'name':bol_order_vals.get('name'),
                                        'global_channel_id': instance.global_channel_id and instance.global_channel_id.id or False,
                                        })
                sale_order = self.create(order_vals) if order_vals else False
                
                if not sale_order:
                    continue
                
                product=False
                for line in lines:
                    bol_product=self.env['bol.product.ept'].search_product(ean=line.EAN,condition=line.OfferCondition,instance_id=instance.id)
                    if not bol_product:
                        continue
                    product_url = bol_product and bol_product.producturl or False
                    product=bol_product.product_id
                    actual_unit_price = 0.0                    
                    actual_unit_price = float(line.OfferPrice) / float(line.Quantity)
                    transaction_fee=hasattr(line, "TransactionFee") and line.TransactionFee or 0
                    line_vals = {
                            'order_id':sale_order.id,
                            'product_id':product.id,
                            'company_id':instance.company_id.id,
                            'description':product.name,
                            'order_qty':line.Quantity,
                            'price_unit':actual_unit_price,
                            }
                    order_line=self.env['sale.order.line'].create_sale_order_line_ept(line_vals)
                    order_line.update({'order_item_id': line.OrderItemId,'bol_transaction_fee':transaction_fee,'producturl': product_url})
                    self.env['sale.order.line'].create(order_line)
                    sale_order.requested_date=line.LatestDeliveryDate.split("+")[0]
                    
                if len(sale_order.order_line)>0:
                    import_order_ids.append(sale_order.id)
                else:
                    sale_order.unlink()
                    bol_job_log_obj.create({
                        'job_id':bol_job.id,
                        'message':"Sale order with id %s is not imported due to all products were not available in odoo."%(order.OrderId),
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'not_found',
                        'bol_instance_id':instance.id
                    })
            if import_order_ids:
                self.env['sale.workflow.process.ept'].auto_workflow_process(ids=import_order_ids)
                odoo_orders=self.browse(import_order_ids)
                for order in odoo_orders:
                    order.invoice_shipping_on_delivery=False
            if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.model
    def get_order_sequence(self,order,order_sequence):
        order_obj=self.env['sale.order']
        new_name = "%s%s" %(order.bol_instance_id.bol_order_prefix and order.bol_instance_id.bol_order_prefix+'_' or '', order.bol_order_number)     
        new_name = new_name +'/'+str(order_sequence)
        if order_obj.search([('name','=',new_name)]):
            order_sequence=order_sequence+1
            return self.get_order_sequence(order,order_sequence)
        else:
            return new_name

    @api.model
    def create_sale_order_line(self,order,line,bol_job):
        instance = order.bol_instance_id
        message=False
        mismatch = self.check_bol_mismatch_details([line],instance,line.OrderId,bol_job)
        if mismatch:
            message=mismatch
            return False,message
        bol_product=self.env['bol.product.ept'].search_product(ean=line.EAN,condition=line.OfferCondition,instance_id=instance.id)
        if not bol_product:
            message="Product with ean %s is not found for order %s"%(line.EAN,order.bol_order_id)
            return False,message
        product_url = bol_product and bol_product.producturl or False
        product=bol_product.product_id
        actual_unit_price = float(line.OfferPrice) / float(line.Quantity)
        line_vals = {
                        'order_id':order.id,
                        'product_id':product.id,
                        'company_id':instance.company_id.id,
                        'description':product.name,
                        'order_qty':line.Quantity,
                        'price_unit':actual_unit_price,
                    }
        bol_line_rec=self.env['sale.order.line'].create_sale_order_line_ept(line_vals)
        bol_line_rec.update({'order_item_id': line.OrderItemId,'producturl':product_url})
        self.env['sale.order.line'].create(bol_line_rec)
        return True,bol_line_rec
    
    @api.multi
    def create_bol_order(self,instance,warehouse,shipment,shipmentitem,fullfillment_by,bol_job):
        bol_job_log_obj=self.env['bol.job.log.ept']
        partner = self.create_or_update_bol_customer(shipment.CustomerDetails, False,False,False,instance)
        if not partner:
            bol_job_log_obj.create({
            'job_id':bol_job.id,
            'message':"Order is skip due to partner not found",
            'operation_type':'import',
            'user_id':self.env.user.id,
            'log_type':'skip',
            'bol_instance_id':instance.id
            })
            return False
        workflow=instance.fbb_order_workflow if fullfillment_by.upper()=="FBB" else instance.fbr_order_workflow
        bol_order_vals=self.get_order_vals(shipmentitem.OrderItem, fullfillment_by, workflow, partner, instance, partner, partner, instance.pricelist_id.id, instance.payment_term_id.id)
        order_vals=self.create_sales_order_vals_ept(bol_order_vals)
        order_vals.update({'bol_order_id':shipmentitem.OrderItem.OrderId,
                                'bol_order_number':shipmentitem.OrderItem.OrderId,
                                'bol_instance_id':instance.id,
                                'fullfillment_method':fullfillment_by.upper(),
                                'auto_workflow_process_id':workflow.id,
                                'name':bol_order_vals.get('name')
                                })
        return self.create(order_vals)
    
    def create_or_update_sale_order(self,shipment,shipmentitem,bol_job,instance,fullfillment_by):
        bol_job_log_obj=self.env['bol.job.log.ept']
        sale_order_line_obj=self.env['sale.order.line']
        order_id=shipmentitem.OrderItem.OrderId
        order=self.search([('bol_order_id','=',order_id),('bol_instance_id','=',instance.id),('fullfillment_method','=',fullfillment_by.upper()),('date_order','=',datetime.strftime(shipment.ShipmentDate,"%Y-%m-%d %H:%M:%S"))])
        if not order:
            order=self.search([('bol_order_id','=',order_id),('bol_instance_id','=',instance.id),('fullfillment_method','=',fullfillment_by.upper()),('state','in',['draft','sent','sale'])])
        if order:
            if order.fullfillment_method.upper()=="FBB" and order.state in ['draft','sent']:
                order.action_confirm()
            order_item_id = shipmentitem.OrderItem.OrderItemId
            bol_line_rec = sale_order_line_obj.search([('order_item_id','=',order_item_id),('order_id','=',order.id)])
            if not bol_line_rec:
                is_line_created,bol_line_rec = self.create_sale_order_line(order,shipmentitem.OrderItem,bol_job)
                if not is_line_created:
                    bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':"Order is skip due to %s"%(bol_line_rec),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'skip',
                    'bol_instance_id':instance.id
                    })
                    return False
            return order
        else:
            warehouse = instance.fbb_warehouse_id if fullfillment_by.upper()=='FBB' else instance.fbr_warehouse_id
            bol_order = self.create_bol_order(instance,warehouse,shipment,shipmentitem,fullfillment_by,bol_job)
            if not bol_order:
                return False
            for shipmentitm in shipment.ShipmentItems:
                is_line_created,bol_line_rec = self.create_sale_order_line(bol_order,shipmentitm.OrderItem,bol_job)
                if not is_line_created:
                    bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':"Order is skip due to %s"%(bol_line_rec),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'skip',
                    'bol_instance_id':instance.id
                    })
                    bol_order.unlink()
                    return False
            bol_job_log_obj.create({
                'job_id':bol_job.id,
                'message':"Order %s created while import shipmets"%(bol_order.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'info',
                'bol_instance_id':instance.id
                })
            bol_order.action_confirm()
            self.env['sale.workflow.process.ept'].auto_workflow_process(ids=[bol_order.id])
            return bol_order
        return order and order or bol_order
    
    def auto_import_bol_fbb_sale_order_ept(self,ctx):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.import_bol_orders(instance,fullfillment_by='FBB')
        return True
    
    def auto_import_bol_fbr_sale_order_ept(self,ctx):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.import_bol_orders(instance)
        return True
    
    @api.model
    def update_bol_order_status(self,instance):
        move_line_obj = self.env['stock.move.line']
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        instances=[]
        if not instance:
            instances=self.env['bol.instance.ept'].search([('order_auto_import','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            plaza_api=instance.connect_in_bol()
            bol_job=log_book_obj.create({
                    'application':'shipment',
                    'message':'Perform Export Shipment operation',
                    'operation_type':'import',
                    'bol_request':'/services/rest/shipments/v2',
                    'bol_instance_id':instance.id
                })    
            sales_orders = self.search([('warehouse_id','=',instance.fbr_warehouse_id.id),
                                                         ('bol_order_id','!=',False),
                                                         ('bol_instance_id','=',instance.id),                                                     
                                                         ('updated_in_bol','=',False)],order='date_order')
            
            for sale_order in sales_orders:
                for picking in sale_order.picking_ids:
                    if picking.updated_in_bol or picking.state!='done':
                        if instance.update_order_status_when_picking_in_ready and picking.updated_in_bol or picking.state!='assigned':
                            continue
                    for move in picking.move_lines:
                        if move.sale_line_id and move.sale_line_id.order_item_id:
                            bol_line_id=move.sale_line_id.order_item_id
                        """Create Package for the each parcel"""
                        move_line = move_line_obj.search([('move_id','=',move.id),('product_id','=',move.product_id.id)],limit=1)
                        if move_line.result_package_id:
                            vals={}
                            tracking_no=False
                            if sale_order.bol_instance_id.bol_manage_multi_tracking_number_in_delivery_order:                                        
                                if move_line.result_package_id.tracking_no:  
                                    tracking_no=move_line.result_package_id.tracking_no
                                if (move_line.package_id and move_line.package_id.tracking_no):  
                                    tracking_no=move_line.package_id.tracking_no
                            else:
                                tracking_no = picking.carrier_tracking_ref or False
                            if instance.update_order_status_when_picking_in_ready and picking.state=='assigned':
                                try:
                                    response=plaza_api.shipments.create(order_item_id=bol_line_id)
                                except Exception as e:
                                    bol_job_log_obj.create({
                                        'job_id':bol_job.id,
                                        'message':e,
                                        'operation_type':'export',
                                        'user_id':self.env.user.id,
                                        'log_type':'error',
                                        'bol_instance_id':instance.id
                                        })
                                    continue
                                bol_job.write({'bol_response':response})
                            else:
                                try:
                                    if picking.bol_trasport_id and not picking.updated_transport_detail and picking.state=='done':
                                        response=plaza_api.transports.update(id=picking.bol_trasport_id,transporter_code=picking.fbr_transport_id.code,track_and_trace=tracking_no)
                                    else:
                                        response=plaza_api.shipments.create(order_item_id=bol_line_id,transporter_code=picking.fbr_transport_id.code,track_and_trace=tracking_no)
                                except Exception as e:
                                    bol_job_log_obj.create({
                                        'job_id':bol_job.id,
                                        'message':e,
                                        'operation_type':'export',
                                        'user_id':self.env.user.id,
                                        'log_type':'error',
                                        'bol_instance_id':instance.id
                                        })
                                    continue
                                bol_job.write({'bol_response':response})
                            if not picking.bol_shipment_id:
                                try:
                                    shipments=plaza_api.shipments.list(shipment_fullfillment_by=sale_order.fullfillment_method.upper(),order_id=sale_order.bol_order_id)
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
                                for shipment in shipments:
                                    for shipmentitem in shipment.ShipmentItems:
                                        if shipmentitem.OrderItem.OrderItemId == move.sale_line_id.order_item_id:
                                            vals.update({'bol_shipment_id':shipment.ShipmentId,'bol_trasport_id':shipment.Transport.TransportId})
                            process_status_id=response.id
                            process_status=response.status
                            event_type=response.eventType
                            vals.update({'process_status':process_status,'bol_process_status_id':process_status_id,'event_type':event_type})
                            if picking.state=='done':
                                vals.update({'updated_in_bol':True,'updated_transport_detail':True})
                            picking.write(vals)
                        else:
                            vals={}
                            if instance.update_order_status_when_picking_in_ready and picking.state=='assigned':
                                try:
                                    response=plaza_api.shipments.create(order_item_id=bol_line_id)
                                except Exception as e:
                                    bol_job_log_obj.create({
                                        'job_id':bol_job.id,
                                        'message':e,
                                        'operation_type':'export',
                                        'user_id':self.env.user.id,
                                        'log_type':'error',
                                        'bol_instance_id':instance.id
                                        })
                                    continue
                                bol_job.write({'bol_response':response})
                            else:
                                try:
                                    if picking.bol_trasport_id and not picking.updated_transport_detail and picking.state=='done':
                                        response=plaza_api.transports.update(id=picking.bol_trasport_id,transporter_code=picking.fbr_transport_id.code,track_and_trace=picking.carrier_tracking_ref)
                                    else:
                                        response=plaza_api.shipments.create(order_item_id=bol_line_id,transporter_code=picking.fbr_transport_id.code,track_and_trace=picking.carrier_tracking_ref)
                                except Exception as e:
                                    bol_job_log_obj.create({
                                        'job_id':bol_job.id,
                                        'message':e,
                                        'operation_type':'export',
                                        'user_id':self.env.user.id,
                                        'log_type':'error',
                                        'bol_instance_id':instance.id
                                        })
                                    continue
                                bol_job.write({'bol_response':response})
                            if not picking.bol_shipment_id:
                                try:
                                    shipments=plaza_api.shipments.list(shipment_fullfillment_by=sale_order.fullfillment_method.upper(),order_id=sale_order.bol_order_id)
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
                                for shipment in shipments:
                                    for shipmentitem in shipment.ShipmentItems:
                                        if shipmentitem.OrderItem.OrderItemId == move.sale_line_id.order_item_id:
                                            vals.update({'bol_shipment_id':shipment.ShipmentId,'bol_trasport_id':shipment.Transport.TransportId})
                            process_status_id=response.id
                            process_status=response.status
                            event_type=response.eventType
                            vals.update({'process_status':process_status,'bol_process_status_id':process_status_id,'event_type':event_type})
                            if picking.state=='done':
                                vals.update({'updated_transport_detail':True,'updated_in_bol':True})
                            picking.write(vals)
        return True
            
    def auto_update_bol_order_status_ept(self,ctx):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.update_bol_order_status(instance)
        return True
        
class sale_order_line(models.Model):
    _inherit="sale.order.line"
    
    order_item_id=fields.Char("Order Item ID")
    bol_transaction_fee=fields.Float('Transaction Fee')
