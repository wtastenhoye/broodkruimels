from odoo import models,fields,api,_
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp
from datetime import datetime
import time
import base64
from _io import StringIO
from odoo.osv import expression

class bol_product_ept(models.Model):
    _name='bol.product.ept'
    
    name=fields.Char('Title',required=True)
    ean=fields.Char('EAN',required=True)
    condition=fields.Selection([('NEW','New'),
                                       ('AS_NEW','As New'),
                                       ('GOOD','Good'),
                                       ('REASONABLE','Reasonable'),
                                       ('MODERATE','Moderate')],'Product Condition',help="Whether the offer refers to a new or second hand product.")
    delivery_code=fields.Selection([('24uurs-23','Ordered before 23:00 on working days, delivered the next working day.'),
                                    ('24uurs-22','Ordered before 22:00 on working days, delivered the next working day.'),
                                    ('24uurs-21','Ordered before 21:00 on working days, delivered the next working day.'),
                                    ('24uurs-20','Ordered before 23:00 on working days, delivered the next working day.'),
                                    ('24uurs-19','Ordered before 19:00 on working days, delivered the next working day.'),
                                    ('24uurs-18','Ordered before 18:00 on working days, delivered the next working day.'),
                                    ('24uurs-17','Ordered before 17:00 on working days, delivered the next working day.'),
                                    ('24uurs-16','Ordered before 16:00 on working days, delivered the next working day.'),
                                    ('24uurs-15','Ordered before 15:00 on working days, delivered the next working day.'),
                                    ('24uurs-14','Ordered before 14:00 on working days, delivered the next working day.'),
                                    ('24uurs-13','Ordered before 13:00 on working days, delivered the next working day.'),
                                    ('24uurs-12','Ordered before 12:00 on working days, delivered the next working day.'),
                                    ('1-2d','1-2 working days.'),
                                    ('2-3d','2-3 working days.'),
                                    ('3-5d','3-5 working days.'),
                                    ('4-8d','4-8 working days.'),
                                    ('1-8d','1-8 working days.'),
                                    ],'Delivery code',help="The delivery promise that applies to this product.")
    publish=fields.Boolean('Publish in bol.com',help="Determining whether the seller desires the product to be offered for sale on the bol.com website or not.")
    fullfillment_method=fields.Selection([('FBR','FBR'),('FBB','FBB')],'Fullfillment Method',default='FBR',required=True)
    reference_code=fields.Char('Reference Code')
    product_description=fields.Text('Description')
    published=fields.Boolean('Published',help="Shows whether or not this offer is published on the website. It is defaulted to N by bol.com if any errors occur in this offer or if out of stock.")
    reason_code=fields.Char("Reason Code",help="if not Published, this field will show the associated error code.")
    reason_message=fields.Char("Reason Message",help="Explains the reason why this offer is not shown if not Published.")
    product_id=fields.Many2one('product.product','Product')
    exported_in_bol=fields.Boolean('Exported In Bol')
    bol_instance_id=fields.Many2one('bol.instance.ept','Instance')
    created_at=fields.Datetime("Created At")
    updated_at=fields.Datetime("Updated At")
    fix_stock_type=fields.Selection([('fix','Fix'),('percentage','Percentage')], string='Fix Stock Type')
    fix_stock_value=fields.Float(string='Fix Stock Value',digits=dp.get_precision("Product UoS"))
    product_status_id=fields.Many2one('bol.product.status.ept','Product Status')
    bol_bsku=fields.Char("BSKU")
    producturl=fields.Text("Product URL")

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = expression.AND([
            args or [],
            ['|','|', ('name', operator, name), ('ean', operator, name),('bol_bsku', operator, name)]
        ])
        return self.search(args, limit=limit).name_get()

    @api.multi
    def search_product(self,ean='',condition='',instance_id=False):
        if not ean or not instance_id:
            return False
        domain=[('ean','=',ean),('bol_instance_id','=',instance_id)]
        condition and domain.append(('condition','=',condition))
        return self.search(domain,limit=1)
    
    @api.multi
    def sync_product(self,instance,ean='',update_price=False):
        if not instance:
            raise Warning("Instance not Available, Can't Process ahed.")
        if not ean:
            return True
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'offer',
                'message':'Perform Sync Product operation for single product',
                'operation_type':'import',
                'bol_request':'/offers/v2/%s'%(ean),
                'bol_instance_id':instance.id
            })
        try:
            response=plaza_api.offers.getSingleOffer(ean=ean)
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
        bol_job.write({'bol_response':response})
        products=[]
        if not response:
            return True
        for product_data in response[0]:
            product={}
            product.update({'ean':product_data.EAN})
            product.update({'condition':product_data.Condition})
            product.update({'price':product_data.Price})
            product.update({'delivery_code':product_data.DeliveryCode})
            product.update({'stock':product_data.QuantityInStock})
            product.update({'publish':product_data.Publish})
            product.update({'reference_code':product_data.ReferenceCode})
            product.update({'description':product_data.Description})
            product.update({'title':product_data.Title})
            product.update({'fullfillment_method':product_data.FulfillmentMethod})
            if hasattr(product_data, 'Status'):
                product.update({'published':product_data.Status and hasattr(product_data.Status, 'Published') and product_data.Status.Published or False})
                product.update({'reason_code':product_data.Status and hasattr(product_data.Status, 'ErrorCode') and product_data.Status.ErrorCode or ''})
                product.update({'reason_message':product_data.Status and hasattr(product_data.Status, 'ErrorMessage') and product_data.Status.ErrorMessage or ''})
            products.append(product)
        self.create_or_update_product(instance, update_price=update_price, job_id=bol_job, products=products)
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.multi
    def create_or_update_product(self,instance,update_price=False,job_id=False,products=[]):
        if not instance:
            raise Warning("Instance not Available, Can't Process ahed.")
        if not products:
            return True
        bol_job_log_obj=self.env['bol.job.log.ept']
        product_template_obj=self.env['product.template']
        product_product_obj=self.env['product.product']
        bol_product_obj=self.env['bol.product.ept']
        for product in products:
            odoo_product=False
            bol_product=False
            ean=product.get('ean')
            title=product.get('title')
            description=product.get('description')
            default_code=product.get('reference_code')
            bol_product=self.search_product(ean=ean,instance_id=instance.id)
            if not bol_product:
                odoo_product=product_product_obj.search([('barcode','=',ean)],limit=1)
            if not odoo_product:
                odoo_product=product_template_obj.search([('barcode','=',ean)],limit=1)
                odoo_product = odoo_product and odoo_product.product_variant_ids[0] or False
            if not bol_product and not odoo_product:
                if instance.auto_create_product:
                    try:
                        odoo_template=product_template_obj.create({
                            'name':title,
                            'barcode':ean,
                            'description_sale':description,
                            'default_code':default_code,
                            'type':'product'
                        })
                        odoo_product=odoo_template.product_variant_ids
                    except Exception as e:
                        bol_job_log_obj.create({
                            'job_id':job_id.id,
                            'message':'Error while create Product with EAN %s\n%s'%(ean,e),
                            'operation_type':'import',
                            'user_id':self.env.user.id,
                            'log_type':'error',
                            'bol_instance_id':self.bol_instance_id.id
                            })
                        continue
                else:
                    bol_job_log_obj.create({
                            'job_id':job_id.id,
                            'message':'Product with EAN %s not found in Odoo.'%(ean),
                            'operation_type':'import',
                            'user_id':self.env.user.id,
                            'log_type':'not_found',
                            'bol_instance_id':self.bol_instance_id.id
                    })
                    continue
            if not odoo_product:
                odoo_product=bol_product.product_id
            vals={  
                    'name':title,
                    'condition':product.get('condition'),
                    'delivery_code':product.get('delivery_code'),
                    'publish':product.get('publish'),
                    'reference_code':default_code,
                    'product_description':product.get('description'),
                    'fullfillment_method':product.get('fullfillment_method'),
                    'published':product.get('published'),
                    'reason_code':product.get('reason_code'),
                    'reason_message':product.get('reason_message'),
                    'updated_at':datetime.now()
                }
            if update_price:
                self.env['product.pricelist'].set_product_price_ept(odoo_product.id,instance.pricelist_id.id,product.get('price'))
            if bol_product:
                bol_product.write(vals)
            else:
                vals.update({'ean':ean,'created_at':datetime.now(),'product_id':odoo_product.id,'exported_in_bol':True,'bol_instance_id':instance.id})
                bol_product_obj.create(vals)
        return True
    
    @api.multi
    def get_stock(self,bol_product,warehouse_id,stock_type='virtual_available'):
        actual_stock=self.env['product.product'].get_stock_ept(bol_product.product_id.id,warehouse_id,stock_type)
        if actual_stock >= 1.00:
            if bol_product.fix_stock_type=='fix':
                if bol_product.fix_stock_value >=actual_stock:
                    return actual_stock
                else:
                    return bol_product.fix_stock_value  
                              
            elif bol_product.fix_stock_type == 'percentage':
                quantity = int(actual_stock * bol_product.fix_stock_value)
                if quantity >= actual_stock:
                    return actual_stock
                else:
                    return quantity
        return actual_stock
    
    @api.multi
    def export_products_in_bol(self,instance,bol_products,is_publish):
        if not instance:
            return True
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'offer',
                'message':'Perform Export/Update Product Operation',
                'operation_type':'export',
                'bol_request':'/offers/v2/',
                'bol_instance_id':instance.id
            })
        product_ids=[]
        batches = []
        bol_product_ids = bol_products.ids
        total_bol_products = len(bol_product_ids)
        
        start,end=0,50
        if total_bol_products > 50:
            while True:                                
                b_product_ids = bol_product_ids[start:end]
                if not b_product_ids:
                    break
                temp=end+50
                start,end=end,temp
                if b_product_ids:
                    products = self.browse(b_product_ids)
                    batches.append(products)
        else:
            batches.append(bol_products)
            
        for products in batches:
            elements=''
            for product in products:
                element="<RetailerOffer>"
                element+="<EAN>%s</EAN>"%(product.ean)
                element+="<Condition>%s</Condition>"%(product.condition)
                element+="<Price>%s</Price>"%(self.env['product.pricelist'].get_product_price_ept(product.product_id,instance.pricelist_id.id))
                element+="<DeliveryCode>%s</DeliveryCode>"%(product.delivery_code)
                element+="<QuantityInStock>%s</QuantityInStock>"%(int(self.get_stock(product,instance.fbr_warehouse_id.id,instance.bol_stock_field.name)))
                element+="<Publish>%s</Publish>"%(str(product.publish).lower())
                element+="<ReferenceCode>%s</ReferenceCode>"%(product.reference_code and product.reference_code or '')
                element+="<Description>%s</Description>"%(product.product_description and product.product_description or '')
                element+="<Title>%s</Title>"%(product.name)
                element+="<FulfillmentMethod>%s</FulfillmentMethod>"%(product.fullfillment_method)
                element+="</RetailerOffer>"
                elements+=element
            xml = """<?xml version="1.0" encoding="UTF-8"?><UpsertRequest xmlns="https://plazaapi.bol.com/offers/xsd/api-2.0.xsd">{elements}</UpsertRequest>""".format(elements=elements)
            try:
                res=plaza_api.offers.upsertOffers(data=xml)
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
            if res==True:
                vals={'updated_at':datetime.now(),'exported_in_bol':True}
                if not product.created_at:
                    vals.update({'created_at':datetime.now()})
                products.write(vals)
                product_ids+=products.ids
            else:
                message=message=res and "Error Code: %s\nError Message: %s"%(res[0][0].ErrorCode,str(res[0][0].ErrorMessage).replace('"https://plazaapi.bol.com/offers/xsd/api-2.0.xsd":', '')) or 'Something went wrong with requested process'
                bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':message,
                    'operation_type':'export',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
                continue
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        if len(product_ids)>0:
            product_status_id=self.env['bol.product.status.ept'].create({'bol_instance_id':instance.id,'created_at':datetime.now(),'bol_product_ids':[(6,0,product_ids)],'state':'draft'})
        return True
     
    @api.multi
    def delete_products_in_bol(self,instance,bol_products):
        if not instance:
            return True
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'offer',
                'message':'Perform Delete Product Operation',
                'operation_type':'delete',
                'bol_request':'/offers/v2/',
                'bol_instance_id':instance.id
            })
        batches = []
        bol_product_ids = bol_products.ids
        total_bol_products = len(bol_product_ids)
        
        start,end=0,1000
        if total_bol_products > 1000:
            while True:                                
                b_product_ids = bol_product_ids[start:end]
                if not b_product_ids:
                    break
                temp=end+1000
                start,end=end,temp
                if b_product_ids:
                    products = self.browse(b_product_ids)
                    batches.append(products)
        else:
            batches.append(bol_products)
            
        for products in batches:
            elements=''
            for product in products:
                element="<RetailerOfferIdentifier>"
                element+="<EAN>%s</EAN>"%(product.ean)
                element+="<Condition>%s</Condition>"%(product.condition)
                element+="</RetailerOfferIdentifier>"
                elements+=element
            xml = """<?xml version="1.0" encoding="UTF-8"?><DeleteBulkRequest xmlns="https://plazaapi.bol.com/offers/xsd/api-2.0.xsd">{elements}</DeleteBulkRequest>""".format(elements=elements)
            try:
                res=plaza_api.offers.deleteOffers(data=xml)
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
            if res==True:
                products.unlink()
            else:
                message=res and "Error Code: %s\nError Message: %s"%(res[0][0].ErrorCode,str(res[0][0].ErrorMessage).replace('"https://plazaapi.bol.com/offers/xsd/api-2.0.xsd":', '')) or 'Something went wrong with requested process'
                bol_job_log_obj.create({
                    'job_id':bol_job.id,
                    'message':message,
                    'operation_type':'export',
                    'user_id':self.env.user.id,
                    'log_type':'error',
                    'bol_instance_id':instance.id
                    })
                continue
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
     
    @api.multi
    def retrive_product_status(self,instance,products):
        if not instance:
            return True
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=instance.connect_in_bol()
        bol_job=log_book_obj.create({
                'application':'offer',
                'operation_type':'import',
                'message':'Perform Get Product Status operation for retrive status of product from bol.com',
                'bol_request':'/offers/v2/',
                'bol_instance_id':instance.id
            })
        for product in products:
            vals={}
            try:
                response=plaza_api.offers.getSingleOffer(ean=product.ean)
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
            vals.update({'published':response[0][0].Status and hasattr(response[0][0].Status, 'Published') and response[0][0].Status.Published or False})
            vals.update({'reason_code':response[0][0].Status and hasattr(response[0][0].Status, 'ErrorCode') and response[0][0].Status.ErrorCode or ''})
            vals.update({'reason_message':response[0][0].Status and hasattr(response[0][0].Status, 'ErrorMessage') and response[0][0].Status.ErrorMessage or ''})
            product.write(vals)
        if bol_job and len(bol_job.transaction_log_ids)==0:bol_job.write({'message':bol_job.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.multi
    def auto_update_stock(self,ctx={}):
        bol_instance_obj=self.env['bol.instance.ept']
        bol_product_obj=self.env['bol.product.ept']
        if not isinstance(ctx,dict) or not 'bol_instance_id' in ctx:
            return True
        bol_instance_id = ctx.get('bol_instance_id',False)
        if bol_instance_id:
            instance=bol_instance_obj.search([('id','=',bol_instance_id)])
            bol_products=bol_product_obj.search([('bol_instance_id','=',instance.id)])
            self.export_products_in_bol(instance,bol_products,instance.is_publish)
        return True
    
class product_sync_ept(models.Model):
    _name='bol.product.sync.ept'
    _inherit = ['mail.thread']
    _order='id desc'
    _description='Product Sync'
    
    bol_instance_id=fields.Many2one('bol.instance.ept',string='Instance')
    name = fields.Char(size=256, string='Reference',default="New")
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    requested_date = fields.Datetime('Requested Date',default=time.strftime("%Y-%m-%d %H:%M:%S"))
    state = fields.Selection([('draft','Draft'),('requested','Requested'),('downloaded','Downloaded'),
                                     ('processed','Processed')
                                     ],
                                    string='Process Status', default='draft')    
    user_id = fields.Many2one('res.users',string="Requested User")
    file_url=fields.Char('File Url')
    job_id=fields.Many2one('bol.process.job.ept','Process Job')
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    
    @api.model
    def create(self,vals):
        try:
            sequence=self.env.ref("bol_ept.seq_bol_product_sync_job")
        except:
            sequence=False
        name=sequence and sequence.next_by_id() or '/'
        if type(vals)==dict:
            vals.update({'name':name})
        vals.update({'user_id':self.env.user.id})
        return super(product_sync_ept, self).create(vals)
    
    @api.multi
    def unlink(self):
        for report in self:
            if report.state == 'processed':
                raise Warning(_('You cannot delete processed record.'))
        return super(product_sync_ept, self).unlink()
    
    @api.multi
    def request_file(self):
        vals={}
        log_book_obj=self.env['bol.process.job.ept']
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=self.bol_instance_id.connect_in_bol()
        if not self.job_id:
            bol_job=log_book_obj.create({
                    'application':'offer',
                    'message':'Perform Operation for Retrive Product Export file from bol.com',
                    'operation_type':'import',
                    'bol_request':'/offers/v2/export',
                    'bol_instance_id':self.bol_instance_id.id
                })
            vals.update({'job_id':bol_job and bol_job.id or False})
        try:
            response=plaza_api.offers.getOffersFileName()
        except Exception as e:
            bol_job and bol_job_log_obj.create({
                'job_id':bol_job.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':self.bol_instance_id.id
                })
            return True
        bol_job.write({'bol_response':response})
        response.Url and vals.update({'file_url':response.Url,'state':'requested'})
        vals and self.write(vals)
        return True    
        
    @api.multi
    def get_file(self):
        if not self.file_url:
            raise Warning('File Url does not exists, Please first request product file')
        bol_job_log_obj=self.env['bol.job.log.ept']
        plaza_api=self.bol_instance_id.connect_in_bol()
        try:
            response=plaza_api.offers.getOffersFile(csv=self.file_url)
        except Exception as e:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':e,
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':self.bol_instance_id.id
                })
            return True
        if not response.__contains__("EAN,Condition,Price,Deliverycode,Stock,Publish,Reference,Description,Title,FulfillmentMethod,Published,ReasonCode,ReasonMessage"):
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':"Response not in proper format\n%s"%(response),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'mismatch',
                'bol_instance_id':self.bol_instance_id.id
                })
            return True
        if response:
            file_name=self.name+time.strftime("%Y_%m_%d_%H%M%S")+"_offers.csv"
            attachment = self.env['ir.attachment'].create({
                                           'name': file_name,
                                           'datas': base64.b64encode(response.encode(encoding='utf_8', errors='strict')),
                                           'datas_fname': file_name,
                                           'res_model': 'mail.compose.message', 
                                           'type': 'binary'
                                         })
            self.message_post(body=_("<b>Product File Downloaded</b>"),attachment_ids=attachment.ids)
            self.write({'attachment_id':attachment.id,
                        'state':'downloaded'
                    })
        return True
    
    @api.multi
    def process_file(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        if not self.attachment_id:
            raise Warning("There is no any report are attached with this record.")
        if not self.bol_instance_id:
            raise Warning("Please select the Instance in report.")
        imp_file = StringIO(base64.decodestring(self.attachment_id.datas).decode('utf-8'))
        content = imp_file.read()
        if not content:
            bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'File has no content or not readable',
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'error',
                'bol_instance_id':self.bol_instance_id.id
                })
            return True
        products=[]
        for line in content.splitlines():
            if line == "EAN,Condition,Price,Deliverycode,Stock,Publish,Reference,Description,Title,FulfillmentMethod,Published,ReasonCode,ReasonMessage":
                continue
            if len(line.split("\",\""))!=13:
                bol_job_log_obj.create({
                'job_id':self.job_id.id,
                'message':'Line %s has not proper data'%(line),
                'operation_type':'import',
                'user_id':self.env.user.id,
                'log_type':'mismatch',
                'bol_instance_id':self.bol_instance_id.id
                })
                continue
            line=line.split("\",\"")
            product_data={}
            product_data.update({'ean':line[0].replace("\"","")})
            product_data.update({'condition':line[1]})
            product_data.update({'price':line[2]})
            product_data.update({'delivery_code':line[3]})
            product_data.update({'stock':line[4]})
            product_data.update({'publish':line[5]})
            product_data.update({'reference_code':line[6]})
            product_data.update({'description':line[7]})
            product_data.update({'title':line[8].replace("\"\",", "\",")})
            product_data.update({'fullfillment_method':line[9]})
            product_data.update({'published':line[10]})
            product_data.update({'reason_code':line[11]})
            product_data.update({'reason_message':line[12]})
            products.append(product_data)
        self.write({'state':'processed'})
        self.env['bol.product.ept'].create_or_update_product(instance=self.bol_instance_id,job_id=self.job_id,update_price=self.bol_instance_id.sync_price_with_product,products=products)
        if self.job_id and len(self.job_id.transaction_log_ids)==0:self.job_id.write({'message':self.job_id.message+"\n\nProcess Completed Successfully."})
        return True
    
    @api.multi
    def list_of_logs(self):
        bol_job_log_obj=self.env['bol.job.log.ept']
        records=bol_job_log_obj.search([('job_id','=',self.job_id.id)])
        action = {
            'domain': "[('id', 'in', " + str(records.ids) + " )]",
            'name': 'Mismatch Logs',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'bol.job.log.ept',
            'type': 'ir.actions.act_window',
                  }
        return action

class product_status_ept(models.Model):
    _name="bol.product.status.ept"
    _order='id desc'
    _description='Product Status'
    
    name=fields.Char('Reference')
    created_at=fields.Datetime('Created At')
    bol_instance_id=fields.Many2one('bol.instance.ept',"Instance")
    state=fields.Selection([('draft','Draft'),('done','Done')],'Status')
    bol_product_ids=fields.One2many('bol.product.ept','product_status_id','Bol Products')
    user_id = fields.Many2one('res.users',string="Requested User")
    
    @api.multi
    def unlink(self):
        for record in self:
            raise Warning(_('You cannot delete record.'))
        return super(product_sync_ept, self).unlink()
    
    @api.model
    def create(self,vals):
        try:
            sequence=self.env.ref("bol_ept.seq_bol_product_status_job")
        except:
            sequence=False
        name=sequence and sequence.next_by_id() or '/'
        if type(vals)==dict:
            vals.update({'name':name})
        vals.update({'user_id':self.env.user.id})
        return super(product_status_ept, self).create(vals)
    
    def get_status(self):
        res=self.env['bol.product.ept'].retrive_product_status(self.bol_instance_id,self.bol_product_ids)
        if res:
            self.write({'state':'done'})
