from odoo import models,fields,api,_

class bol_fbb_transport_ept(models.Model):
    _name='bol.fbb.transport.ept'
    
    name=fields.Char('Name')
    code=fields.Char('Code')
    bol_instance_id=fields.Many2one('bol.instance.ept','Instance')
    carrier_id=fields.Many2one('delivery.carrier',"Delivery Method")
    
    def import_transport(self,instance):
        transaction_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        try:
            response=plaza_api.fbbtransports.getFbbTransports()
        except Exception as e:
            transaction_log_obj.create({'message':e,
                 'operation_type':'import',
                 'user_id':self.env.user.id,
                 'log_type':'error'})
            return True
        for transport in response:
            code=transport.Code
            name=transport.Name
            transport=self.search([('code','=',code),('bol_instance_id','=',instance.id)],limit=1)
            if transport:
                transport.write({'name':name})
            else:
                self.create({'name':name,'code':code,'bol_instance_id':instance.id})
        return True