from odoo import models,fields,api,_

class bol_process_job_ept(models.Model):
    _name='bol.process.job.ept'
    _order='id desc'
    
    name=fields.Char('Name')
    bol_instance_id=fields.Many2one('bol.instance.ept',"Bol Instance")
    application=fields.Selection([('offer','Offer'),
                                  ('order','Order'),
                                  ('inventory','Inventory'),
                                  ('return','Return'),
                                  ('shipment','Shipment'),
                                  ('inbound_shipment','Inbound Shipment'),
                                  ],'Application')
    operation_type=fields.Selection([('import','Import'),
                                   ('export','Export'),
                                   ('update','Update'),
                                   ('delete','Delete')],'Process Type')
    bol_request=fields.Text('Request')
    bol_response=fields.Text('Response')
    message=fields.Text("Message")
    transaction_log_ids=fields.One2many('bol.job.log.ept','job_id','Transaction Logs')
    
    @api.model
    def create(self,vals):
        try:
            sequence=self.env.ref("bol_ept.seq_bol_file_process_job")
        except:
            sequence=False
        name=sequence and sequence.next_by_id() or '/'
        if type(vals)==dict:
            vals.update({'name':name})
        return super(bol_process_job_ept, self).create(vals)
    
class bol_job_log_ept(models.Model):
    _name='bol.job.log.ept'
    _order='id desc'
    _rec_name='job_id'
    
    job_id=fields.Many2one('bol.process.job.ept','Process Job',ondelete="cascade")
    product_id=fields.Many2one('product.product','Product')
    ean=fields.Char('EAN')
    message=fields.Text('Message')
    operation_type=fields.Selection([('import','Import'),
                                   ('export','Export'),
                                   ('update','Update'),
                                   ('delete','Delete')],'Operation Type')
    create_date=fields.Datetime('Create Date')
    user_id=fields.Many2one('res.users','User')
    log_type=fields.Selection([('not_found','Not Found'),
                               ('mismatch','Mismatch'),
                               ('error','Error'),
                               ('warning','Warning'),
                               ('skip','Skip'),
                               ('info','Info')],'Log Type')
    bol_instance_id=fields.Many2one('bol.instance.ept',"Bol Instance")
    