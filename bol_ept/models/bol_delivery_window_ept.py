from odoo import models,fields,api,_
from odoo.exceptions import Warning

class bol_delivery_window_ept(models.Model):
    _name='bol.delivery.window.ept'
    _rec_name='start_datetime'
    
    @api.multi
    def name_get(self):
        result = []
        for s in self:
            if s.start_datetime and s.end_datetime:
                name = "%s  %s"%(s.start_datetime,s.end_datetime)
                result.append((s.id, name))
        return result
    
    start_datetime=fields.Char('Start DateTime')
    end_datetime=fields.Char('End DateTime')
    bol_instance_id=fields.Many2one('bol.instance.ept','Instance')
    bol_shipment_id=fields.Many2one('bol.inbound.shipment.ept',"Shipment Id",default=0)
    delivery_date=fields.Datetime("Delivery Date")
    items_to_send=fields.Integer("Items to send")
    
    def import_delivery_window(self):
        if not self.delivery_date:
            raise Warning("Delivery Date is not available.")
        if not self.items_to_send:
            raise Warning("Items to send is not available.")
        inbound_shipment_id=self._context.get('inbound_shipment_id')
        if not inbound_shipment_id:
            raise Warning("Inbound Shipment Id not available.")
        inbound_shipment=self.env['bol.inbound.shipment.ept'].browse(inbound_shipment_id)
        instance=inbound_shipment.bol_instance_id
        transaction_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        try:
            response=plaza_api.inbounds.getDeliveryWindow(delivery_date=self.delivery_date.split(" ")[0],qty_to_send=self.items_to_send)
        except Exception as e:
            transaction_log_obj.create({'message':e,
                 'operation_type':'import',
                 'user_id':self.env.user.id,
                 'log_type':'error'})
            return True
        for delivery_window in response:
            start_date=delivery_window.Start
            end_date=delivery_window.End
            delivery_window=self.search([('start_datetime','=',start_date),('end_datetime','=',end_date),('bol_instance_id','=',instance.id),('bol_shipment_id','=',inbound_shipment_id)],limit=1)
            if not delivery_window:
                self.create({'start_datetime':start_date,'end_datetime':end_date,'bol_instance_id':instance.id,'bol_shipment_id':inbound_shipment_id})
        inbound_shipment.write({'is_delivery_window_received':True})
        return {'type': 'ir.actions.client','tag': 'reload'} 
