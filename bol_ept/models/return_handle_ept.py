from odoo import models,fields,api,_
from odoo.exceptions import Warning,AccessError

class ReturnHandleEpt(models.Model):
    _name='return.handle.ept'
    _inherit=['mail.thread']
    _description="Return Request"
         
    @api.constrains('return_qty')
    def check_qty(self):
        for record in self:
            if record.return_qty <=0:
                raise Warning("Quantity must be positive number.")
    
    name=fields.Char("Return Number")
    return_reason=fields.Char('Return Reason')
    description=fields.Text('Return Reason Comments')
    sale_id=fields.Many2one('sale.order',"Order")
    partner_id=fields.Many2one('res.partner',"Customer")
    return_date=fields.Date("Date")
    product_id=fields.Many2one('product.product',"Product")
    qty=fields.Float("Requested Quantity")
    return_qty=fields.Float("Received Quantity")
    state=fields.Selection([('draft','Draft'),('process','Processing'),('close','Closed')],default='draft')
    action=fields.Selection([('PRODUCT_RECEIVED','PRODUCT_RECEIVED'),
                             ('REPAIRED','REPAIRED'),
                             ('EXCHANGED','EXCHANGED'),
                             ('FAILS_TO_MATCH_RETURN_CONDITIONS','FAILS_TO_MATCH_RETURN_CONDITIONS'),
                             ('CUSTOMER_KEEPS_PRODUCT','CUSTOMER_KEEPS_PRODUCT')],'Action')
    bol_instance_id=fields.Many2one('bol.instance.ept',"Bol Instance",required=True)
    process_status=fields.Selection([('PENDING','PENDING'),
                                     ('FAILURE','FAILURE'),
                                     ('TIMEOUT','TIMEOUT'),
                                     ('SUCCESS','SUCCESS')],'Process Status')
    error_message=fields.Text('Error Message')
    bol_process_status_id=fields.Char("Bol Process Status ID")
    process_description=fields.Char("Process Description")
    event_type=fields.Char('Event Type',readonly="1")
    
    @api.multi
    def import_return_requests(self,instance):
        if not instance:
            return False
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'order',
                'message':'Perform Import return requests',
                'operation_type':'import',
                'bol_request':'/services/rest/return-items/v2/unhandled',
                'bol_instance_id':instance.id
            })
        try:
            responses=plaza_api.return_items.getUnhandled()
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
        bol_job.write({'bol_response':responses})
        for response in responses:
            if self.search([('name','=',response.ReturnNumber)]):
                continue
            vals={}
            vals.update({'name':response.ReturnNumber})
            sale_id=self.env['sale.order'].search([('bol_order_id','=',response.OrderId),('bol_instance_id','=',instance.id)],limit=1)
            if not sale_id:
                bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':"Sale order not found for Return request no. %s"%(response.ReturnNumber),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
                continue
            vals.update({'sale_id':sale_id.id})
            vals.update({'return_date':response.ReturnDateAnnouncement,'return_reason':response.ReturnReason,'description':response.ReturnReasonComments})
            product_id=self.env['product.product'].search([('barcode','=',response.EAN)])
            if not product_id:
                bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':"Product not found for Return request no. %s"%(response.ReturnNumber),
                    'operation_type':'import',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
                continue
            vals.update({'product_id':product_id.id,'qty':response.Quantity,'partner_id':sale_id.partner_id.id,'bol_instance_id':instance.id})
            handle_return=self.create(vals)
            if instance.is_auto_start_return:
                handle_return.start_claim()
        return True
    
    @api.multi
    def start_claim(self):
        if not self.sale_id:
            raise Warning("Sale order is not available, can't process.")
        self.state='process'
        return True
    
    @api.multi
    def unlink(self):
        for record in self:
            if record.state!='draft':
                raise Warning("You can't delete return request which is not in Draft state.")
        return super(ReturnHandleEpt,self).unlink()
    
    @api.multi
    def process_claim(self):
        if not self.bol_instance_id:
            raise Warning("Instance is not set")
        if not self.action:
            raise Warning("Please set appropriate Action to update in Bol.com")
        if not self.return_qty:
            raise Warning("Please set Received Quantity to update in Bol.com")
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=self.bol_instance_id.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'order',
                'message':'Perform update return requests',
                'operation_type':'update',
                'bol_request':'/services/rest/return-items/v2/:id/handle',
                'bol_instance_id':self.bol_instance_id.id
            })
        try:
            if self.action=="REPAIRED" or self.action=="EXCHANGED":
                action="REPAIRED_OR_EXCHANGED"
            else:
                action=self.action
            response=plaza_api.return_items.getHandle(self.name, action, int(self.qty))
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':bol_job.id,
                'message':e,
                'operation_type':'update',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':self.bol_instance_id.id
                })
            return True
        bol_job.write({'bol_response':response})
        process_status_id=response.id
        process_status=response.status
        event_type=response.eventType
        process_description=response.description
        vals={'process_status':process_status,'bol_process_status_id':process_status_id,'event_type':event_type,'process_description':process_description,'state':'close'}
        self.write(vals)
        return True
    
    @api.multi
    def show_pickings(self):
        return {
            'name': "Delivery",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'domain':[('id','in',self.sale_id.picking_ids.ids)]
            }
    
    @api.multi
    def get_process_status(self):
        if not self.bol_process_status_id:
            raise Warning("Process Status Id not found.")
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        instance=self.bol_instance_id
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'shipment',
                'message':'Perform Retrive Shipment status',
                'operation_type':'import',
                'bol_request':'/services/rest/process-status/v2',
                'bol_instance_id':instance.id
            })    
        try:
            response=plaza_api.process_status.get(self.bol_process_status_id)
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
        self.write({'error_message':error_message,'process_status':process_status})
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(ReturnHandleEpt, self).message_get_suggested_recipients()
        try:
            for record in self:
                if record.partner_id:
                    record._message_add_suggested_recipient(recipients, partner=record.partner_id, reason=_('Customer'))
                elif record.email_from:
                    record._message_add_suggested_recipient(recipients, email=record.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients