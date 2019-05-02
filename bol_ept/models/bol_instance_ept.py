from odoo import models,fields,api,_
from odoo.exceptions import Warning
from .. bol import plaza

class bol_instance_ept(models.Model):
    _name='bol.instance.ept'
    
    @api.model
    def _default_stock_field(self):
        qty_available = self.env['ir.model.fields'].search([('model_id.model','=','product.product'),('name','=','qty_available')],limit=1)
        return qty_available and qty_available.id
    
    name=fields.Char('Name')
    company_id=fields.Many2one('res.company','Company',required=1)
    fbr_warehouse_id=fields.Many2one('stock.warehouse','FBR Warehouse')
    fbb_warehouse_id=fields.Many2one('stock.warehouse','FBB Warehouse')
    pricelist_id=fields.Many2one('product.pricelist','Price List')
    bol_lang_id=fields.Many2one('res.lang','Language')
    auto_workflow_id=fields.Many2one('sale.workflow.process.ept','Auto Workflow')
    auto_create_product=fields.Boolean('Auto create product?')
    auto_validate_inventory=fields.Boolean('Auto Validate Inventory (FBB)')
    bol_order_prefix=fields.Char('Order Prefix')
    public_key=fields.Char('Public Key')
    private_key=fields.Text('Private Key')
    test_environment=fields.Boolean('Test Environment',default=False)
    inventory_last_sync_on=fields.Datetime('Inventory last sync on')
    payment_term_id=fields.Many2one('account.payment.term','Payment Term')
    default_codition=fields.Selection([('NEW','New'),
                                       ('AS_NEW','As New'),
                                       ('GOOD','Good'),
                                       ('REASONABLE','Reasonable'),
                                       ('MODERATE','Moderate')],'Default Offer/Product Condition')
    default_delivery_code=fields.Selection([('24uurs-23','Ordered before 23:00 on working days, delivered the next working day.'),
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
                                            ],'Default delivery code')
    bol_stock_field = fields.Many2one('ir.model.fields', string='Stock Field', default=_default_stock_field)
    bol_country_id=fields.Many2one("res.country","Country")
    bol_team_id=fields.Many2one('crm.team', 'Sales Team')
    bol_fulfillment_by=fields.Selection([('FBR','FBR'),('FBM','FBM')],'Fullfillment By')
    state=fields.Selection([('not_confirmed','Not Confirmed'),('confirmed','Confirmed')],default='not_confirmed')
    is_publish = fields.Boolean(string="Publish In Bol.com?",default=False)
    color = fields.Integer(string='Color Index')
    sync_price_with_product=fields.Boolean("Sync/Import Product Price?",help="Check if you want to import price along with products",default=False)
    fbb_order_auto_import = fields.Boolean(string='Auto Import FBB Order?',help="Check if you want to automatically import FBB orders at certain interval.")
    fbr_order_auto_import = fields.Boolean(string='Auto Import FBR Order?',help="Check if you want to automatically import FBR orders at certain interval.")
    auto_import_shipment = fields.Boolean(string='Auto Import Shipment?',help="Check if you want to automatically import Shipmets at certain interval.")
    auto_update_stock = fields.Boolean(string='Auto Update Stock?',help="Check if you want to automatically update stock at certain interval.")
    fbr_order_workflow=fields.Many2one('sale.workflow.process.ept',"FBR Order Auto Workflow")
    fbb_order_workflow=fields.Many2one('sale.workflow.process.ept',"FBB Order Auto Workflow")
    import_shipment_order_type=fields.Selection([('fbb','FBB Orders'),('all','All Orders')],"Import Shipment for",default='fbb')
    bol_manage_multi_tracking_number_in_delivery_order=fields.Boolean("One order can have multiple Tracking Number ?",default=False)
    last_imported_shipment=fields.Date("Last Imported Shipments on")
    check_shipment_for_days=fields.Integer("Check Shipment For Days",default=0)
    bol_order_auto_update=fields.Boolean(string="Auto Order Update ?")
    auto_retrive_shipment_status = fields.Boolean("Auto Retrive Shipment Statuses?")
    update_order_status_when_picking_in_ready=fields.Boolean("Is Update Order Status When Picking is in Ready State?")
    validate_bol_stock_inventory = fields.Boolean("Auto Validate FBB Inventory Stock")
    auto_import_fbb_inventory = fields.Boolean("Auto Import FBB Inventory?")
    allow_process_unshipped_bol_products=fields.Boolean("Allow Process Unshipped Products in Inbound Shipment ?",default=False)
    is_auto_start_return=fields.Boolean("Auto Start Order Returns?")
    global_channel_id = fields.Many2one('global.channel.ept', string="Global Channel")

    def _count_all(self):
        for instance in self:
            instance.fbm_quotation_count = len(instance.fbm_quotation_ids)
            instance.fbm_order_count = len(instance.fbm_order_ids)
            instance.fbb_quotation_count = len(instance.fbb_quotation_ids)
            instance.fbb_order_count = len(instance.fbb_order_ids)
            instance.exported_product_count = len(instance.exported_product_ids)
            instance.ready_to_export_product_count = len(instance.ready_to_export_product_ids)
            instance.picking_count = len(instance.picking_ids)
            instance.invoice_count = len(instance.invoice_ids)
            instance.confirmed_picking_count = len(instance.confirmed_picking_ids)
            instance.assigned_picking_count = len(instance.assigned_picking_ids)
            instance.partially_available_picking_count = len(instance.partially_available_picking_ids)
            instance.done_picking_count = len(instance.done_picking_ids)
            instance.assigned_picking_count = len(instance.assigned_picking_ids)
            
            draft_inbound_shipments=self.env['bol.inbound.shipment.ept'].search([('bol_instance_id','=',instance.id),('state','=','draft')])
            instance.count_draft_inbound_shipments=len(draft_inbound_shipments)
            submitted_inbound_shipments=self.env['bol.inbound.shipment.ept'].search([('bol_instance_id','=',instance.id),('state','=','submitted')])
            instance.count_submitted_inbound_shipments=len(submitted_inbound_shipments)
            
    fbm_quotation_ids = fields.One2many('sale.order','bol_instance_id',domain=[('state','in',['draft','sent']),('fullfillment_method','=','FBR')],string="Quotations")        
    fbm_quotation_count = fields.Integer(compute='_count_all', string="Quotations")
        
    fbm_order_ids = fields.One2many('sale.order','bol_instance_id',domain=[('state','not in',['draft','sent','cancel']),('fullfillment_method','=','FBR')],string="Sales Order")
    fbm_order_count =fields.Integer(compute='_count_all', string="Sales Order")
    
    fbb_quotation_ids = fields.One2many('sale.order','bol_instance_id',domain=[('state','in',['draft','sent']),('fullfillment_method','=','FBB')],string="Quotations")        
    fbb_quotation_count = fields.Integer(compute='_count_all', string="Quotations")
        
    fbb_order_ids = fields.One2many('sale.order','bol_instance_id',domain=[('state','not in',['draft','sent','cancel']),('fullfillment_method','=','FBB')],string="Sales Order")
    fbb_order_count =fields.Integer(compute='_count_all', string="Sales Order")
    
    exported_product_ids = fields.One2many('bol.product.ept', 'bol_instance_id', string='Exported Products',domain=[('exported_in_bol','=',True)])
    exported_product_count = fields.Integer(compute='_count_all', string="Exported Products")
     
    ready_to_export_product_ids = fields.One2many('bol.product.ept','bol_instance_id',domain=[('exported_in_bol','=',False)],string="Ready To Export")
    ready_to_export_product_count = fields.Integer(compute='_count_all', string="Ready To Export")
    picking_ids = fields.One2many('stock.picking','bol_instance_id',string="Pickings")
    picking_count = fields.Integer(compute='_count_all', string="Pickings") 
    invoice_ids = fields.One2many('account.invoice','bol_instance_id',string="Invoices")
    invoice_count = fields.Integer(compute='_count_all', string="Invoices")
     
    confirmed_picking_ids = fields.One2many('stock.picking','bol_instance_id',domain=[('state','=','confirmed')],string="Confirm Pickings")
    confirmed_picking_count =fields.Integer(compute='_count_all', string="Confirm Pickings")
    assigned_picking_ids = fields.One2many('stock.picking','bol_instance_id',domain=[('state','=','assigned')],string="Assigned Pickings")
    assigned_picking_count =fields.Integer(compute='_count_all', string="Assigned Pickings")
    partially_available_picking_ids = fields.One2many('stock.picking','bol_instance_id',domain=[('state','=','partially_available')],string="Partially Available Pickings")
    partially_available_picking_count =fields.Integer(compute='_count_all', string="Partially Available Pickings")
    done_picking_ids = fields.One2many('stock.picking','bol_instance_id',domain=[('state','=','done')],string="Done Pickings")
    done_picking_count =fields.Integer(compute='_count_all', string="Done Pickings")
     
    count_draft_inbound_shipments=fields.Integer(string="Count Draft Inbound Shipment Plan",compute="_count_all")
    count_submitted_inbound_shipments=fields.Integer(string="Count Submitted Inbound Shipment Plan",compute="_count_all")
    
    @api.multi
    def test_bol_connection(self):
        plaza_api=plaza.api.PlazaAPI(self.public_key, self.private_key, test=self.test_environment)
        flag = False
        try:
            result = plaza_api.orders.list()
            if isinstance(result, list):
                flag=True
        except Exception as e:
            raise Warning('Given Credential is incorrect, please provide correct Credential.')
        if flag:
            raise Warning('Service Working Properly')
        return True
    
    @api.multi
    def reset_to_confirm(self):
        self.write({'state':'not_confirmed'})
        return True
    
    @api.multi
    def confirm(self):        
        plaza_api=plaza.api.PlazaAPI(self.public_key, self.private_key, test=self.test_environment)
        try:
            result = plaza_api.orders.list()
            if isinstance(result, list):
                self.write({'state':'confirmed'})
        except Exception as e:
            raise Warning('Given Credential is incorrect, please provide correct Credential.')            
        return True              
        
    @api.model
    def connect_in_bol(self):
        plaza_api=plaza.api.PlazaAPI(self.public_key, self.private_key, test=self.test_environment)
        return plaza_api
    