from odoo import models,fields,api,_
from xml.etree import ElementTree as etree
import base64
import logging
_logger = logging.getLogger(__name__)

class product_label_format_ept(models.TransientModel):
    _name="product.label.format.ept"
    
    label_format=fields.Selection([('AVERY_J8159','AVERY_J8159'),('AVERY_J8160','AVERY_J8160'),('AVERY_3474','AVERY_3474'),('DYMO_99012','DYMO_99012'),('BROTHER_DK11208D','BROTHER_DK11208D'),('ZEBRA_Z_PERFORM_1000T','ZEBRA_Z_PERFORM_1000T')],"Product Label Format")
        
    def get_product_lables(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self._context:
            return False
        shipment=self.env['bol.inbound.shipment.ept'].search([('id','=',self._context.get('inbound_shipment_id'))],limit=1)
        if not shipment:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Shipment not found in shipment',
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                })
            return False
        if not shipment.bol_instance_id:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Instance not found in shipment %s'%(shipment.name),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'not_found',
                })
            return True
        instance=shipment.bol_instance_id
        plaza_api=instance.connect_in_bol()
        
        root = etree.Element("Productlabels")
        root.attrib['xmlns']="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd"
        for shipment_line in shipment.shipment_line_ids:
            product=etree.SubElement(root,"Productlabel")
            etree.SubElement(product,"EAN").text=shipment_line.barcode
            etree.SubElement(product,"Quantity").text=str(int(shipment_line.quantity))
        try:
            response=plaza_api.inbounds.getProductLabel(product_data=etree.tostring(root,encoding='UTF-8').decode("UTF-8"),format=self.label_format)
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':shipment.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':instance.id
                })
            return False
        if response:
            file_name=shipment.name+"_product_labels.pdf"
            attachment = self.env['ir.attachment'].create({
                                           'name': file_name,
                                           'datas': base64.encodestring(response),
                                           'datas_fname': file_name,
                                           'res_model': 'mail.compose.message', 
                                           'type': 'binary'
                                         })
            shipment.message_post(body=_("<b>Product Label File Downloaded</b>"),attachment_ids=attachment.ids)
        return True