from odoo import models,fields,api,_
from datetime import datetime,timedelta
from odoo.tools.float_utils import float_round, float_compare

class stock_picking(models.Model):
    _inherit='stock.picking'
    
    @api.onchange('fbb_transport_id','fbr_transport_id')
    def on_change_transport_id(self):
        for record in self:
            if record.fbb_transport_id:
                record.carrier_id=record.fbb_transport_id.carrier_id
            if record.fbr_transport_id:
                record.carrier_id=record.fbr_transport_id.carrier_id
    
    @api.multi
    def _get_total_received_qty(self):
        for picking in self:
            total_shipped_qty=0.0
            total_received_qty=0.0
            for move in picking.move_lines:
                if move.state=='done':
                    total_received_qty+=move.product_qty
                    total_shipped_qty+=move.product_qty
                if move.state not in ['draft','cancel']:
                    total_shipped_qty+=move.reserved_availability
            picking.total_received_qty=total_received_qty
            picking.total_shipped_qty=total_shipped_qty
    
    bol_instance_id=fields.Many2one('bol.instance.ept',"Instance")
    is_bol_delivery_order=fields.Boolean('Bol Delivery Order')
    updated_in_bol=fields.Boolean('Updated In Bol')
    canceled_in_bol=fields.Boolean('Canceled In Bol')
    fbb_transport_id=fields.Many2one('bol.fbb.transport.ept','FBB Transport')
    fbr_transport_id=fields.Many2one('bol.fbr.transport.ept','FBR Transport')
    bol_process_status_id=fields.Char("Bol Process Status ID")
    process_status=fields.Selection([('PENDING','PENDING'),
                                     ('FAILURE','FAILURE'),
                                     ('TIMEOUT','TIMEOUT'),
                                     ('SUCCESS','SUCCESS')],'Process Status')
    error_message=fields.Text('Error Message')
    inbound_shipment_id=fields.Many2one('bol.inbound.shipment.ept','Inbound Shipment')
    bol_shipment_id=fields.Char("Bol Shipment ID")
    fullfillment_method=fields.Selection([('FBR','FBR'),('FBB','FBB')],'Fullfillment Method',readonly=True)
    updated_transport_detail=fields.Boolean("Is Transport details Updated?")
    bol_trasport_id=fields.Char("Bol Transport ID")
    event_type=fields.Char('Event Type',readonly="1")
    is_fbb_wh_picking = fields.Boolean("Is FBB Warehouse Picking",default=False,copy=True)
    bol_odoo_shipment_id = fields.Many2one('bol.inbound.shipment.ept', readonly=True,default=False,copy=True, string="Bol Inbound Shiment")
    bol_shipment_id =fields.Char("Bol Shipment Id")
    total_received_qty=fields.Float(compute=_get_total_received_qty,string="Total Received Qty")
    total_shipped_qty=fields.Float(compute=_get_total_received_qty,string="Total Shipped Qty")
    
    @api.multi
    def mark_sent_bol(self):
        for picking in self:
            picking.write({'updated_in_bol':False})
        return True
    
    @api.multi
    def mark_not_sent_bol(self):
        for picking in self:
            picking.write({'updated_in_bol':True})
        return True
    
    @api.multi
    def import_shipments(self,instance,shipment_fullfillment_by='fbb'):
        instances=[]
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        picking_obj = self.env['stock.picking']
        bol_product_obj = self.env['bol.product.ept']
        if not instance:
            instances=self.env['bol.instance.ept'].search([('auto_import_shipment','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            bol_job=log_book_obj.create({
                    'application':'shipment',
                    'message':'Perform Import Shipment operation',
                    'operation_type':'import',
                    'bol_request':'/services/rest/shipments/v2',
                    'bol_instance_id':instance.id
                })
            shipments=[]
            page=0
            warehouse=False
            plaza_api=instance.connect_in_bol()
            try:
                while True:
                    if page==-1: break
                    page=page+1
                    responses=[]
                    responses=plaza_api.shipments.list(shipment_fullfillment_by=shipment_fullfillment_by.upper(),page=page)
                    if responses:
                        for response in responses:
                            if datetime.strptime(response.ShipmentDate.strftime('%Y-%m-%d'),'%Y-%m-%d') >= (datetime.strptime(instance.last_imported_shipment,'%Y-%m-%d')-timedelta(days=instance.check_shipment_for_days)):
                                shipments.append(response)
                            else:
                                page=-1
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
            bol_job.write({'bol_response':shipments})
            for shipment in shipments:
                pick_ids = []
                if self.search([('bol_shipment_id','=',shipment.ShipmentId),('bol_instance_id','=',instance.id)]):
                    continue
                for shipmentitem in shipment.ShipmentItems:
                    fullfillment_by=shipmentitem.OrderItem.FulfilmentMethod
                    order=self.env['sale.order'].create_or_update_sale_order(shipment,shipmentitem,bol_job,instance,fullfillment_by=fullfillment_by)
                    if not order:
                        bol_job_log_obj.create({
                            'job_id':bol_job.id,
                            'message':"Order not found for shipment with id %s"%(shipment.ShipmentId),
                            'operation_type':'import',
                            'user_id':self.env.user.id,
                            'log_type':'not_found',
                            'bol_instance_id':instance.id
                        })
                        continue
                    if fullfillment_by=="FBB":
                        warehouse=instance.fbb_warehouse_id
                    else:
                        warehouse=instance.fbr_warehouse_id
                    if len(order.picking_ids) > 1:
                        pickings = picking_obj.search([('state','in',['confirmed','assigned','partially_available']),
                                                      ('id','in',order.picking_ids.ids),
                                                      ('picking_type_id.warehouse_id','=',warehouse and warehouse.id)
                                                      ])
                    else:
                        pickings = order.picking_ids
                    if not pickings:
                        continue
                    order.invoice_shipping_on_delivery=False
                    pickings.action_confirm()
                    if not order.auto_workflow_process_id.auto_check_availability:
                        if pickings.state not in 'done,cancel' : pickings.action_assign()
                    for picking in pickings:
                        picking_vals={}
                        if not picking.bol_shipment_id or not picking.carrier_id:
                            picking_vals.update({'bol_shipment_id':shipment.ShipmentId,'date_done':datetime.now()})
                        bol_fbb_transport=False
                        bol_fbr_transport=False
                        if order.fullfillment_method=='FBB':
                            bol_fbb_transport=self.env['bol.fbb.transport.ept'].search([('code','=',shipment.Transport.TransporterCode),('bol_instance_id','=',instance.id)])
                            if not bol_fbb_transport:
                                bol_fbb_transport=self.env['bol.fbb.transport.ept'].create({'code':shipment.Transport.TransporterCode,'name':shipment.Transport.TransporterCode,'bol_instance_id':instance.id})
                        else:
                            bol_fbr_transport=self.env['bol.fbr.transport.ept'].search([('code','=',shipment.Transport.TransporterCode)])
                        if bol_fbb_transport:
                            picking_vals.update({'fbb_transport_id':bol_fbb_transport.id})
                            bol_fbb_transport.carrier_id and picking_vals.update({'carrier_id':bol_fbb_transport.carrier_id.id})
                        if bol_fbr_transport:
                            picking_vals.update({'fbr_transport_id':bol_fbr_transport.id})
                            bol_fbr_transport.carrier_id and picking_vals.update({'carrier_id':bol_fbr_transport.carrier_id.id})
                        picking_vals and picking.write(picking_vals)
                        
                        ean=shipmentitem.OrderItem.EAN
                        condition=shipmentitem.OrderItem.OfferCondition
                        bol_product = bol_product_obj.search_product(ean,condition,order.bol_instance_id.id)
                        product=bol_product and bol_product.product_id or False
                        file_qty = shipmentitem.OrderItem.Quantity
                        if order.bol_instance_id.bol_manage_multi_tracking_number_in_delivery_order:
                            datas = {product.id:{'product_qty':file_qty,'traking_no':shipment.Transport.TrackAndTrace}}
                            picking_obj.process_delivery_order(picking_id=picking.id,datas=datas)
                        else:
                            datas = [{'product_id':product.id,'product_qty':file_qty}]
                            picking_obj.process_delivery_order_ept(picking_id=picking.id,datas=datas,traking_no=shipment.Transport.TrackAndTrace)
                        pick_ids.append(picking.id)
                pick_ids and picking_obj.browse(list(set(pick_ids))).write({'updated_in_bol':True})
            instance.write({'last_imported_shipment':datetime.now()})
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
    
    @api.multi
    def auto_import_shipment(self,ctx={}):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.import_shipments(instance,shipment_fullfillment_by=instance.import_shipment_order_type)
        return True
        
    @api.multi
    def get_process_status(self,instance=False,stock_picking=False):
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        if instance and isinstance(instance, type(self.bol_instance_id)):
            instances=instance
        elif self:
            instances=self.bol_instance_id
        else:
            instances= self.env['bol.instance.ept'].search([('state','=','confirmed')])
        for instance in instances:
            plaza_api=instance.connect_in_bol()
            bol_job=log_book_obj.create({
                    'application':'shipment',
                    'message':'Perform Retrive Shipment status',
                    'operation_type':'import',
                    'bol_request':'/services/rest/process-status/v2',
                    'bol_instance_id':instance.id
                })    
            if stock_picking:
                pickings = stock_picking
            else:
                pickings = self.search([('process_status','=','PENDING')])
            for picking in pickings:
                try:
                    response=plaza_api.process_status.get(picking.bol_process_status_id)
                except Exception as e:
                    bol_job_log_obj.create({
                        'job_id':bol_job.id,
                        'message':e,
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'error',
                        'bol_instance_id':instance.id
                        })
                    return False
                bol_job.write({'bol_response':response})
                process_status=response.status
                error_message=hasattr(response,"errorMessage") and response.errorMessage or ''
                picking.write({'error_message':error_message,'process_status':process_status})
            if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.multi
    def auto_retrive_delivery_status_ept(self,ctx={}):
        bol_instance_obj=self.env['bol.instance.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id),('state','=','confirmed')])
            self.get_process_status(instance)
        return True
    
    @api.multi
    def check_bol_shipment_status(self,bol_shipment,instance):
        if self.ids:
            pickings = self
        else:
            pickings = self.search([('state','in',['partially_available','assigned']),
                                    ('bol_odoo_shipment_id','!=',False),
                                    ('bol_shipment_id','!=',False),
                                    ('is_fbb_wh_picking','=',True)])

        move_obj = self.env['stock.move']
        bol_product_obj = self.env['bol.product.ept']
        stock_move_line_obj=self.env['stock.move.line']
        bol_shipment_ids=[]
        process_picking=False
        for picking in pickings:
            bol_shipment_ids.append(picking.bol_odoo_shipment_id.id)
            for item in bol_shipment.Products:
                ean = item.EAN
                shipped_qty=item.AnnouncedQuantity
                received_qty = float(item.ReceivedQuantity)
                bol_product = bol_product_obj.search_product(ean=ean,instance_id=instance.id)
                if not bol_product:
                    bol_product=bol_product_obj.search([('ean','=',ean),('instance_id','=',instance.id)])
                if not bol_product:
                    picking.message_post(body=_("""Product not found in ERP ||| 
                                                EAN : %s
                                                Shipped Qty : %s
                                                Received Qty : %s                          
                                             """%(ean,shipped_qty,received_qty)))
                    continue
                odoo_product_id = bol_product and bol_product.product_id.id or False
                done_moves=move_obj.search([('picking_id.is_fbb_wh_picking','=',True),('picking_id.bol_shipment_id','=',picking.bol_shipment_id),('product_id','=',odoo_product_id),('state','=','done')],order="id")
                source_location_id=done_moves and done_moves[0].location_id.id
                for done_move in done_moves:
                    if done_move.location_dest_id.id!=source_location_id:
                        received_qty=received_qty-done_move.product_qty
                    else:
                        received_qty=received_qty+done_move.product_qty                        
                if received_qty <=0.0:
                    continue
                move_lines = move_obj.search([('picking_id','=',picking.id),('product_id','=',odoo_product_id),('state','not in',('draft','done','cancel','waiting'))])                                                
                if not move_lines:
                    move_lines = move_obj.search([('picking_id','=',picking.id),('product_id','=',odoo_product_id),('state','not in',('draft','done','cancel'))])                                                
                for move_line in move_lines:
                    if move_line.state=='waiting':
                        move_line.force_assign()
                if not move_lines and instance.allow_process_unshipped_bol_products:
                    process_picking=True
                    move=picking.move_lines[0]
                    odoo_product=bol_product.product_id
                    new_move = move_obj.create({
                        'name': _('New Move:') + odoo_product.display_name,
                        'product_id': odoo_product.id,
                        'product_uom_qty':received_qty,
                        'product_uom': odoo_product.uom_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'picking_id': picking.id,
                    })
                    stock_move_line_obj.create(
                        {
                            'product_id':move.product_id.id,
                            'product_uom_id':move.product_id.uom_id.id, 
                            'picking_id':picking.id,
                            'qty_done':float(received_qty) or 0,
                            'ordered_qty':float(received_qty) or 0,
                            'location_id':picking.location_id.id,
                            'location_dest_id':picking.location_dest_id.id,
                            'move_id':new_move.id,
                         })
                elif not move_lines and not instance.allow_process_unshipped_bol_products:
                    picking.message_post(body=_("""Line skipped due to move not found in ERP ||| 
                                                EAN : %s  
                                                Shipped Qty : %s
                                                Received Qty : %s                          
                                             """%(ean,shipped_qty,received_qty)))
                qty_left=received_qty
                for move in move_lines:
                    process_picking=True
                    if move.state=='waiting':
                        move.force_assign()
                    if qty_left<=0.0:
                        break
                    move_line_remaning_qty=(move.product_uom_qty)-(sum(move.move_line_ids.mapped('qty_done')))
                    operations=move.move_line_ids.filtered(lambda o: o.qty_done <= 0)
                    for operation in operations:
                        if operation.product_uom_qty<=qty_left:
                            op_qty=operation.product_uom_qty
                        else:
                            op_qty=qty_left
                        operation.write({'qty_done':op_qty})
                        self._put_in_pack_ept(operation)
                        qty_left=float_round(qty_left -op_qty,precision_rounding=operation.product_uom_id.rounding,rounding_method='UP')
                        move_line_remaning_qty=move_line_remaning_qty-op_qty
                        if qty_left<=0.0:
                            break
                    if qty_left>0.0 and move_line_remaning_qty>0.0:
                        if move_line_remaning_qty<=qty_left:
                            op_qty=move_line_remaning_qty
                        else:
                            op_qty=qty_left
                        stock_move_line_obj.create(
                            {
                                    'product_id':move.product_id.id,
                                    'product_uom_id':move.product_id.uom_id.id, 
                                    'picking_id':picking.id,
                                    'qty_done':float(op_qty) or 0,
                                    'ordered_qty':float(op_qty) or 0,
                                    'result_package_id':False,
                                    'location_id':picking.location_id.id, 
                                    'location_dest_id':picking.location_dest_id.id,
                                    'move_id':move.id,
                             })
                        qty_left=float_round(qty_left -op_qty,precision_rounding=move.product_id.uom_id.rounding,rounding_method='UP')
                        if qty_left<=0.0:
                            break
                if qty_left>0.0:
                    stock_move_line_obj.create(
                        {
                            'product_id': move_lines[0].product_id.id,
                            'product_uom_id':move_lines[0].product_id.uom_id.id, 
                            'picking_id':picking.id,
                            'ordered_qty':float(qty_left) or 0,
                            'qty_done':float(qty_left) or 0,
                            'result_package_id':False,
                            'location_id':picking.location_id.id, 
                            'location_dest_id':picking.location_dest_id.id,
                            'move_id':move_lines[0].id,
                         })
            process_picking and picking.action_done()
        return True
    
    @api.model
    def check_qty_difference_and_create_return_picking(self,bol_shipment_id,bol_odoo_shipment_id,instance,bol_shipment):
        pickings = self.search([('state','=','done'),
                                ('bol_odoo_shipment_id','=',bol_odoo_shipment_id),
                                ('bol_shipment_id','=',bol_shipment_id),
                                ('is_fbb_wh_picking','=',True)],order="id")
        stock_immediate_transfer_obj=self.env['stock.immediate.transfer']
        location_id=pickings[0].location_id.id
        location_dest_id=pickings[0].location_dest_id.id
        move_obj=self.env['stock.move']
        return_picking=False
        bol_product_obj = self.env['bol.product.ept']
        for item in bol_shipment.Products:
            ean = item.EAN
            received_qty = float(item.ReceivedQuantity)
            bol_product = bol_product_obj.search_product(ean=ean,instance_id=instance.id)
            if not bol_product:
                bol_product=bol_product_obj.search([('ean','=',ean),('instance_id','=',instance.id)])
            if not bol_product:
                continue            
            done_moves=move_obj.search([('picking_id.is_fbb_wh_picking','=',True),
                                        ('picking_id.bol_shipment_id','=',bol_shipment_id),
                                        ('product_id','=',bol_product.product_id.id),
                                        ('state','=','done'),
                                        ('location_id','=',location_id),('location_dest_id','=',location_dest_id)])            
            if received_qty <=0.0:
                if not done_moves:
                    continue
            for done_move in done_moves:
                received_qty=received_qty-done_move.product_qty            
            if received_qty<0.0:
                return_moves=move_obj.search([('picking_id.is_fbb_wh_picking','=',True),
                                            ('picking_id.bol_shipment_id','=',bol_shipment_id),
                                            ('product_id','=',bol_product.product_id.id),
                                            ('state','=','done'),
                                            ('location_id','=',location_dest_id),('location_dest_id','=',location_id)])            
                for return_move in return_moves:
                    received_qty=received_qty+return_move.product_qty            
                if received_qty>=0.0:
                    continue
                if not return_picking:
                    pick_type_id = pickings[0].picking_type_id.return_picking_type_id and pickings[0].picking_type_id.return_picking_type_id.id or pickings[0].picking_type_id.id                
                    return_picking = pickings[0].copy({
                        'move_lines': [],
                        'picking_type_id': pick_type_id,
                        'state': 'draft',
                        'origin': bol_shipment_id,
                        'location_id':done_moves[0].location_dest_id.id,
                        'location_dest_id':done_moves[0].location_id.id,
                    })
                received_qty=abs(received_qty)
                for move in done_moves:
                    if move.product_qty<=received_qty:
                        return_qty=move.product_qty
                    else:
                        return_qty=received_qty
                    move.copy({
                        'product_id': move.product_id.id,
                        'product_uom_qty': abs(received_qty),
                        'picking_id': return_picking.id,
                        'state': 'draft',
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': move.location_id.id,
                        'picking_type_id': pick_type_id,
                        'warehouse_id': pickings[0].picking_type_id.warehouse_id.id ,
                        'origin_returned_move_id': move.id,
                        'procure_method': 'make_to_stock',
                        'move_dest_id': False,
                    })
                    received_qty=received_qty-return_qty
                    if received_qty<=0.0:
                        break                
        if return_picking:
            return_picking.action_confirm()
            if return_picking.state not in 'done,cancel': return_picking.action_assign()
            stock_immediate_transfer_obj.create({'pick_id':return_picking.id}).process()
        return True
        