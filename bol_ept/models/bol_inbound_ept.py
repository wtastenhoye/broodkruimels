from odoo import models,fields,api,_
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from xml.etree import ElementTree as etree
import base64
from .. xml_to_dict import response as xml_to_dict

class bol_inbound_ept(models.Model):
    _name='bol.inbound.shipment.ept'
    _description = "Inbound Shipment"
    _inherit = ['mail.thread']
    _order='id desc'
    
    name=fields.Char('Name',default="New")
    warehouse_id=fields.Many2one('stock.warehouse',"Warehouse",domain=[('is_fbb_warehouse','=',False)])
    delivery_window_id=fields.Many2one('bol.delivery.window.ept','Delivery Window')
    fbb_trasnport_id=fields.Many2one('bol.fbb.transport.ept','Transport')
    labelling_service=fields.Boolean('Labeling Service', help="True indicates that you want to use bol.com labellingservice, which means bol.com will place the BSKU labels on your products when they arrive. If you don’t want to use bol.com labellingservice use False when you’re creating your inbound.")
    created_date=fields.Datetime('Create Date')
    updated_in_bol=fields.Boolean('Updated in Bol')
    state=fields.Selection([('draft','Draft'),('submitted','Submitted')],"Shipment Status",default="draft")
    picking_ids=fields.One2many('stock.picking', 'bol_odoo_shipment_id',string="Picking", readonly=True)
    shipment_line_ids=fields.One2many('bol.inbound.shipment.line.ept','bol_inbound_id',"Shipment Items")
    bol_instance_id=fields.Many2one('bol.instance.ept',"Instance")
    process_status_id=fields.Char("Process Status Id")
    process_status=fields.Selection([('PENDING','PENDING'),
                                     ('FAILURE','FAILURE'),
                                     ('TIMEOUT','TIMEOUT'),
                                     ('SUCCESS','SUCCESS')],'Process Status')
    error_message=fields.Text('Error Message')
    event_type=fields.Char("Event Type")
    bol_shipment_id=fields.Char("Shipment Id")
    is_delivery_window_received=fields.Boolean("Delivery Window Received?")
    product_lable_retrived=fields.Boolean("Product Lable Retrived")
    shipping_lable_retrived=fields.Boolean("Shipping Lable Retrived")
    packaging_list_received=fields.Boolean("Packaging List Retrived")
    job_id=fields.Many2one('bol.process.job.ept',"Bol Job")
        
    @api.model
    def create(self,vals):
        try:
            sequence=self.env.ref('bol_ept.seq_bol_inbound_shipment_ept')
            if sequence:
                name=sequence.next_by_id()
            else:
                name='/'
        except:
            name='/'
        vals.update({'name':name})
        return super(bol_inbound_ept,self).create(vals)
    
    @api.multi
    def unlink(self):
        for record in self:
            if record.state=="submitted":
                raise Warning("You cannot delete submitted Shipments")
        return super(bol_inbound_ept,self).unlink()
    
    @api.multi
    def get_delivery_window(self):
        return {
            'name':_("Get Delivery Window"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'bol.delivery.window.ept',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': "{'inbound_shipment_id':active_id}",
        }
    
    @api.multi
    def create_inbound_shipment_ept(self):
        if not self.delivery_window_id:
            raise Warning("Please select appropriate Delivery Window.")
        if not self.fbb_trasnport_id:
            raise Warning("Please select appropriate Transport.")
        bol_job_log_obj=self.env['bol.job.log.ept']
        log_book_obj=self.env['bol.process.job.ept']
        inbound_shipment_line_obj=self.env['bol.inbound.shipment.line.ept']
        if not self.bol_instance_id:
            raise Warning("Instance not found")
        instance=self.bol_instance_id
        plaza_api=instance.connect_in_bol()
        if not inbound_shipment_line_obj.search([('id','in',self.shipment_line_ids.ids)]):
            raise Warning("No product were found for create shipment.")
        
        lines=inbound_shipment_line_obj.search([('id','in',self.shipment_line_ids.ids),('quantity','<=',0.0)])
        if lines:
            raise Warning("Quantity must be greater then zero")
        bol_job=log_book_obj.create({
                    'application':'shipment',
                    'message':'Perform Export Inbound Shipment operation',
                    'operation_type':'export',
                    'bol_request':'/services/rest/inbounds',
                    'bol_instance_id':self.bol_instance_id.id
                })
        root = etree.Element("InboundRequest")
        root.attrib['xmlns']="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd"
        etree.SubElement(root,"Reference").text=self.name
        time_slot=etree.SubElement(root,"TimeSlot")
        etree.SubElement(time_slot,"Start").text=self.delivery_window_id.start_datetime
        etree.SubElement(time_slot,"End").text=self.delivery_window_id.end_datetime
        transport=etree.SubElement(root, "FbbTransporter")
        etree.SubElement(transport,"Code").text=self.fbb_trasnport_id.code
        etree.SubElement(transport,"Name").text=self.fbb_trasnport_id.name
        etree.SubElement(root,"LabellingService").text="true" if self.labelling_service else "false"
        products=etree.SubElement(root,"Products")
        for shipment_line in self.shipment_line_ids:
            product=etree.SubElement(products,"Product")
            etree.SubElement(product,"EAN").text=shipment_line.barcode
            etree.SubElement(product,"AnnouncedQuantity").text=str(shipment_line.quantity)
        try:
            response=plaza_api.inbounds.create_shipment(etree.tostring(root,encoding='UTF-8').decode("UTF-8"))
        except Exception as e:
            bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':e,
                    'operation_type':'export',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
            return True
        bol_job.write({'bol_response':response})
        process_status_id=response.id
        process_status=response.status
        event_type=response.eventType
        self.write({'state':'submitted','process_status':process_status,'process_status_id':process_status_id,'event_type':event_type,'job_id':bol_job.id})
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        
    @api.multi
    def get_process_status(self,instance=False,stock_picking=False):
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self.bol_instance_id:
            return True
        instance=self.bol_instance_id
        plaza_api=instance.connect_in_bol()
        bol_job=self.job_id or log_book_obj.create({
                'application':'shipment',
                'message':'Perform Retrive Shipment status',
                'operation_type':'import',
                'bol_request':'/services/rest/process-status/v2',
                'bol_instance_id':instance.id
            })
        try:
            response=plaza_api.process_status.get(self.process_status_id)
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
        self.write({'job_id':bol_job and bol_job.id or False})
        process_status=response.status
        error_message=hasattr(response,"errorMessage") and response.errorMessage or ''
        self.write({'error_message':error_message,'process_status':process_status})
        if process_status=="SUCCESS":
            res=True
            if not self.bol_shipment_id:
                res=self.get_inbound_shipment_id()
            if not res:
                return False
            self.create_procurements(bol_job)
        return True
    
    @api.model
    def get_inbound_shipment_id(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self.bol_instance_id:
            return True
        instance=self.bol_instance_id
        plaza_api=instance.connect_in_bol()
        page=0
        try:
            while True:
                page=page+1
                if page > 10:
                    bol_job_log_obj.create({
                        'job_id':self.job_id.id,
                        'message':'Unable to retrive Inbound Shipment ID',
                        'operation_type':'import',
                        'user_id':self.env.user.id,
                        'log_type':'error',
                        'bol_instance_id':instance.id
                        })
                    return False
                shipments=xml_to_dict.Response(plaza_api.inbounds.getInboundShipmentList(page=page))
                for shipment in shipments.dict().get('Inbounds').get('Inbound'):
                    if self.name==shipment.get('Reference'):
                        self.write({'bol_shipment_id':shipment.get('Id')})
                        return True
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':instance.id
                })
            return False
        return True
    
    @api.model
    def create_procurements(self,job=False):
        proc_group_obj = self.env['procurement.group']
        picking_obj = self.env['stock.picking']
        location_route_obj = self.env['stock.location.route']
        bol_job_log_obj=self.env['bol.job.log.ept']
        log_book_obj=self.env['bol.process.job.ept']  
        proc_group = proc_group_obj.create({'bol_odoo_shipment_id':self.id,'name':self.name})
        warehouse=self.bol_instance_id.fbb_warehouse_id
        if not warehouse:
            if not job:
                job=log_book_obj.create({'application':'other',
                                           'operation_type':'export',
                                           'instance_id':self.bol_instance_id.id,
                                           'skip_process':True
                                           })
            error_value='FBB warehouse not found, Please first set FBB warehouse in settings.'
            bol_job_log_obj.create({'log_type':'not_found',
                                 'operation_type':'export',
                                 'message':error_value,
                                 'job_id':job.id
                                 })                
            return False
        location_routes = location_route_obj.search([('supplied_wh_id','=',warehouse.id),('supplier_wh_id','=',self.warehouse_id.id)])
        if not location_routes:
            if not job:
                job=log_book_obj.create({'application':'other',
                                           'operation_type':'export',
                                           'instance_id':self.bol_instance_id.id,
                                           'skip_process':True
                                           })
            error_value='Location routes are not found. Please configure routes in warehouse properly || warehouse %s & shipment %s.'%(warehouse.name,self.name)
            bol_job_log_obj.create({'log_type':'not_found',
                                 'operation_type':'export',
                                 'message':error_value,
                                 'job_id':job.id
                                 })                
            return False
        location_routes = location_routes[0]
        
        for line in self.shipment_line_ids:
            qty = line.quantity
            bol_product = line.product_id
            datas={'route_ids':location_routes, 
                   'group_id':proc_group,                       
                   'company_id':self.bol_instance_id.company_id.id, 
                   'warehouse_id': warehouse, 
                   'priority': '1'
                   }
            self.env['procurement.group'].run(bol_product.product_id,qty,bol_product.product_id.uom_id,warehouse.lot_stock_id,bol_product.name,self.name,datas)
        picking = picking_obj.search([('group_id','=',proc_group.id),('picking_type_id.warehouse_id','=',warehouse.id)])
        if picking:
            picking.write({'is_fbb_wh_picking':True})
        return True
    
    @api.multi
    def get_product_label(self):
        if not self.shipment_line_ids:
            raise Warning("No product were found for generate label.")
        return {
            'name':_("Get Product Label"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'product.label.format.ept',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': "{'inbound_shipment_id':active_id}",
        }
    
    @api.multi
    def get_shipping_label(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self.bol_instance_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Instance not found in shipment %s'%(self.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                })
            return False
        instance=self.bol_instance_id
        if not self.bol_shipment_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Inbound Shipment ID is not found in shipment %s'%(self.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                'bol_instance_id':instance.id
                })
            return False
        plaza_api=instance.connect_in_bol()
        try:
            response=plaza_api.inbounds.getShipmentLabel(inbound_id=self.bol_shipment_id)
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':instance.id
                })
            return False
        if response:
            file_name=self.name+"_shipment_labels.pdf"
            attachment = self.env['ir.attachment'].create({
                                           'name': file_name,
                                           'datas': base64.encodestring(response),
                                           'datas_fname': file_name,
                                           'res_model': 'mail.compose.message', 
                                           'type': 'binary'
                                         })
            self.message_post(body=_("<b>Shipment Label File Downloaded</b>"),attachment_ids=attachment.ids)
        return True
    
    @api.multi
    def get_packaging_list(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self.bol_instance_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Instance not found in shipment %s'%(self.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                })
            return False
        instance=self.bol_instance_id
        if not self.bol_shipment_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Inbound Shipment ID is not found in shipment %s'%(self.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                'bol_instance_id':instance.id
                })
            return False
        plaza_api=instance.connect_in_bol()
        try:
            response=plaza_api.inbounds.getPackagingList(inbound_id=self.bol_shipment_id)
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':instance.id
                })
            return False
        if response:
            file_name=self.name+"_packaging_list.pdf"
            attachment = self.env['ir.attachment'].create({
                                           'name': file_name,
                                           'datas': base64.encodestring(response),
                                           'datas_fname': file_name,
                                           'res_model': 'mail.compose.message', 
                                           'type': 'binary'
                                         })
            self.message_post(body=_("<b>Packaging List File Downloaded</b>"),attachment_ids=attachment.ids)
        return True
    
    @api.multi
    def get_remaining_qty(self,instance,odoo_shipment_rec,bol_shipment):
        bol_product_obj=self.env['bol.product.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        move_obj=self.env['stock.move']
        stock_immediate_transfer_obj=self.env['stock.immediate.transfer']
        stock_picking_obj=self.env['stock.picking']
        new_picking=False
        picking = stock_picking_obj.search([('state','=','done'),
                        ('bol_odoo_shipment_id','=',odoo_shipment_rec and odoo_shipment_rec[0].id),
                        ('is_fbb_wh_picking','=',True)],order="id asc",limit=1)
        if not picking:
            picking = stock_picking_obj.search([('state','=','cancel'),
                            ('bol_odoo_shipment_id','=',odoo_shipment_rec and odoo_shipment_rec[0].id),
                            ('is_fbb_wh_picking','=',True)],limit=1)
        
        for item in bol_shipment.Products:
            ean = item.EAN
            received_qty = float(item.ReceivedQuantity)
            if received_qty <=0.0:
                continue
            bol_product = bol_product_obj.search_product(ean=ean,instance_id=instance.id)
            if not bol_product:
                bol_product=bol_product_obj.search([('ean','=',ean),('instance_id','=',instance.id)])
            if not bol_product:
                bol_job_log_obj.create({
                    'job_id':self.job_id.id,
                    'message':'Product with EAN %s not found'%(ean),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'not_found',
                    'bol_instance_id':instance.id
                    })
                continue
            odoo_product = bol_product and bol_product.product_id or False
            done_moves=move_obj.search([('picking_id.is_fbb_wh_picking','=',True),('picking_id.bol_shipment_id','=',bol_shipment.Id),('product_id','=',odoo_product.id),('state','=','done')],order="id")
            source_location_id=done_moves and done_moves[0].location_id.id
            for done_move in done_moves:
                if done_move.location_dest_id.id!=source_location_id:
                    received_qty=received_qty-done_move.product_qty
                else:
                    received_qty=received_qty+done_move.product_qty                        
            if received_qty <=0.0:
                continue
            if not new_picking:
                new_picking=picking.copy({'is_fbb_wh_picking':True,'move_lines':False,'group_id':False,
                                          'location_id':picking.location_id.id,
                                          'location_dest_id':picking.location_dest_id.id,
                                          })
            move=picking.move_lines[0]
            move.copy({'picking_id':new_picking.id,
                                'product_id':odoo_product.id,
                                'product_uom_qty':received_qty,
                                'product_uom':odoo_product.uom_id.id,
                                'procure_method':'make_to_stock',
                                'group_id':False,
                                })
        if new_picking:
            new_picking.action_confirm()
            new_picking.action_assign()
            stock_immediate_transfer_obj.create({'pick_id':new_picking.id}).process()
        return True
    
    @api.multi
    def get_shipment_status(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        stock_picking_obj=self.env['stock.picking']
        if not self.bol_instance_id:
            return True
        instance=self.bol_instance_id
        plaza_api=instance.connect_in_bol()
        if not self.bol_shipment_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Inbound Shipment Id not found',
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                'bol_instance_id':instance.id
                })
            return False
        try:
            shipment=plaza_api.inbounds.getInboundShipment(self.bol_shipment_id)
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':instance.id
                })
            return False
        if not shipment.State=="ArrivedAtWH":
            return False
        shipmentid=shipment.Id
        shipment_status=shipment.State
        odoo_shipment_rec = self.search([('bol_shipment_id','=',shipmentid)])
        pickings = stock_picking_obj.search([('state','in',['partially_available','assigned']),
                                    ('bol_odoo_shipment_id','=',odoo_shipment_rec and odoo_shipment_rec[0].id),
                                    ('is_fbb_wh_picking','=',True)])
        if pickings:
            pickings.check_bol_shipment_status(shipment,instance)
            stock_picking_obj.check_qty_difference_and_create_return_picking(shipmentid,odoo_shipment_rec.id,instance,shipment)
        else:
            pickings = stock_picking_obj.search([('state','in',['draft','waiting','confirmed']),
                            ('bol_odoo_shipment_id','=',odoo_shipment_rec and odoo_shipment_rec[0].id),
                            ('is_fbb_wh_picking','=',True)])

            if pickings:
                self.get_remaining_qty(instance,odoo_shipment_rec,shipment)
            else:
                raise Warning("""Shipment Status is not update due to picking not found for processing  |||
                                Bol status : %s
                                ERP status  : %s
                            """%(shipment_status,odoo_shipment_rec.state))
        return True
    
class bol_inbound_line_ept(models.Model):
    _name='bol.inbound.shipment.line.ept'
    
    @api.onchange("product_id")
    def on_change_product(self):
        for record in self:
            record.barcode=record.product_id.ean
            
    @api.multi
    def get_product_ean(self):
        for record in self:
            record.barcode=record.product_id.ean
    
    product_id=fields.Many2one('bol.product.ept','Product')
    quantity=fields.Integer('Quantity')
    barcode=fields.Char("EAN",compute=get_product_ean)
    bol_inbound_id=fields.Many2one('bol.inbound.shipment.ept',"Bol Inbound Shipment")