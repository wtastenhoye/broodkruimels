from odoo import models,fields,api,_
from odoo.exceptions import Warning
from .. bol import plaza
from datetime import datetime
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class bol_instance_config(models.TransientModel):
    _name='res.config.bol.instance'
    
    name=fields.Char('Name',required=True)
    public_key=fields.Char('Public Key',required=True)
    private_key=fields.Text('Private Key',required=True)
    test_environment=fields.Boolean('Test Environment',default=False)
    bol_country_id = fields.Many2one('res.country',string="Country",required=True)
    
    @api.multi
    def test_bol_connection(self):
        instance_exist = self.env['bol.instance.ept'].search([('public_key','=', self.public_key),
                                                ('private_key','=',self.private_key)])
        if instance_exist:
            raise Warning('Instance already exist with given Credential.')
        
        plaza_api=plaza.api.PlazaAPI(self.public_key, self.private_key, test=self.test_environment)
        flag = True
        try:
            result = plaza_api.orders.list()
            if isinstance(result, list):
                flag=True
        except Exception as e:
            raise Warning('Given Credential is incorrect, please provide correct Credential.')
        if flag:
            vals = {
                    'name':self.name,
                    'public_key':self.public_key,
                    'private_key' : self.private_key,
                    'test_environment':self.test_environment,
                    'bol_country_id':self.bol_country_id.id,
                    'company_id':self.env.user.company_id.id,
                    }        
            try:
                bol_instance = self.env['bol.instance.ept'].create(vals)
            except Exception as e:
                raise Warning('Exception during instance creation.\n %s'%(str(e)))
            return True
        return True

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    @api.model
    def _default_instance(self):
        instances = self.env['bol.instance.ept'].search([])
        return instances and instances[0].id or False
    
    @api.model
    def _get_default_company(self):
        company_id = self.env.user._get_company()
        if not company_id:
            raise Warning(_('There is no default company for the current user!'))
        return company_id
    
    bol_instance_id=fields.Many2one('bol.instance.ept',"Instance",default=_default_instance)
    bol_company_id=fields.Many2one('res.company','Company',default=_get_default_company,help="Orders and Invoices will be generated of this company.")
    fbr_warehouse_id=fields.Many2one('stock.warehouse','FBR Warehouse')
    fbb_warehouse_id=fields.Many2one('stock.warehouse','FBB Warehouse')
    bol_pricelist_id=fields.Many2one('product.pricelist','Price List')
    bol_lang_id=fields.Many2one('res.lang','Language')
    auto_workflow_id=fields.Many2one('sale.workflow.process.ept','Auto Workflow')
    auto_create_product=fields.Boolean('Auto create product if not found?')
    auto_validate_inventory=fields.Boolean('Auto Validate Inventory (FBB)')
    bol_order_prefix=fields.Char('Order Prefix')
    order_auto_import=fields.Boolean('Auto import orders')
    public_key=fields.Char('Public Key')
    private_key=fields.Text('Private Key')
    inventory_last_sync_on=fields.Datetime('Inventory last sync on')
    bol_payment_term_id=fields.Many2one('account.payment.term','Payment Term')
    default_codition=fields.Selection([('NEW','New'),
                                       ('AS_NEW','As New'),
                                       ('GOOD','Good'),
                                       ('REASONABLE','Reasonable'),
                                       ('MODERATE','Moderate')],'Default Offer/Product Condition')
    default_delivery_code=fields.Selection([('24uurs-23','Ordered before 23:00 on working days, delivered the next working day.'),
                                            ('24uurs-22','Ordered before 22:00 on working days, delivered the next working day.'),
                                            ('24uurs-21','Ordered before 21:00 on working days, delivered the next working day.'),
                                            ('24uurs-20','Ordered before 20:00 on working days, delivered the next working day.'),
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
    bol_stock_field = fields.Many2one('ir.model.fields', string='Stock Field')
    bol_country_id=fields.Many2one("res.country","Country")
    bol_team_id=fields.Many2one('crm.team', 'Sales Channel')
    bol_fulfillment_by=fields.Selection([('FBR','FBR'),('FBM','FBM')],'Fullfillment By')
    is_publish = fields.Boolean(string="Publish In Bol.com?",default=False)
    sync_price_with_product=fields.Boolean("Sync/Import Product Price?",help="Check if you want to import price along with products",default=False)
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?")
    
    fbb_order_auto_import = fields.Boolean(string='Auto Import FBB Order?',help="Check if you want to automatically import FBB orders at certain interval.")
    fbb_order_import_interval_number = fields.Integer('Import Order Interval Number',help="Repeat every x.",default=10)
    fbb_order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Order Interval Unit')
    fbb_order_import_next_execution = fields.Datetime('Next Execution', help='Next execution time')
    fbb_order_import_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    
    fbr_order_auto_import = fields.Boolean(string='Auto Import FBR Order?',help="Check if you want to automatically import FBR orders at certain interval.")
    fbr_order_import_interval_number = fields.Integer('Import Order Interval Number',help="Repeat every x.",default=10)
    fbr_order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Order Interval Unit')
    fbr_order_import_next_execution = fields.Datetime('Next Execution', help='Next execution time')
    fbr_order_import_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    
    auto_update_stock = fields.Boolean(string='Auto Update Stock?',help="Check if you want to automatically update stock at certain interval.")
    update_stock_interval_number = fields.Integer('Update Stock Interval Number',help="Repeat every x.",default=10)
    update_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Stock Interval Unit')
    update_stock_next_execution = fields.Datetime('Next Execution', help='Next execution time')
    update_stock_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    fbr_order_workflow=fields.Many2one('sale.workflow.process.ept',"Auto Workflow (FBR)")
    fbb_order_workflow=fields.Many2one('sale.workflow.process.ept',"Auto Workflow (FBB)")
    import_shipment_order_type=fields.Selection([('fbb','FBB Orders'),('all','All Orders')],"Import Shipment for",default='fbb')
    bol_manage_multi_tracking_number_in_delivery_order=fields.Boolean("One order can have multiple Tracking Number ?",default=False)
    auto_import_shipment=fields.Boolean(string='Auto Import Shipmets?',help="Check if you want to automatically import shipmets at certain interval.")
    import_shipment_interval_number = fields.Integer('Import Shipments Interval Number',help="Repeat every x.",default=10)
    import_shipment_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Stock Interval Unit')
    import_shipment_next_execution = fields.Datetime('Next Execution', help='Next execution time')
    import_shipment_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    bol_order_auto_update=fields.Boolean(string="Auto Order Update ?",help="Check if you want to automatically update order status to Bol.")
    bol_order_update_interval_number = fields.Integer('Update Order Interval Number',help="Repeat every x.",default=10)
    bol_order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')               
    bol_order_update_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    bol_order_update_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    auto_retrive_shipment_status = fields.Boolean("Auto Retrive Shipment Statuses?")
    retrive_shipment_status_interval_number = fields.Integer('Retrive Shipment Statuses Interval Number',help="Repeat every x.",default=10)
    retrive_shipment_status_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')               
    retrive_shipment_status_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    retrive_shipment_status_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    update_order_status_when_picking_in_ready=fields.Boolean("Is Update Order Status When Picking is in Ready State?")
    validate_bol_stock_inventory = fields.Boolean("Auto Validate FBB Inventory Stock")
    auto_import_fbb_inventory = fields.Boolean("Auto Import FBB Inventory?")
    import_fbb_inventory_interval_number = fields.Integer('Import FBB Inventory Interval Number',help="Repeat every x.",default=10)
    import_fbb_inventory_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')               
    import_fbb_inventory_next_execution = fields.Datetime('Next Execution', help='Next execution time')    
    import_fbb_inventory_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    allow_process_unshipped_bol_products=fields.Boolean("Allow Process Unshipped Products in Inbound Shipment ?",default=False)
    is_auto_start_return=fields.Boolean("Auto Start Order Returns?")
    bol_global_channel_id = fields.Many2one('global.channel.ept', string="Global Channel")

    @api.onchange('bol_instance_id')
    def onchange_bol_instance_id(self):
        instance = self.bol_instance_id or False
        self.bol_company_id=instance and instance.company_id and instance.company_id.id or False
        self.fbr_warehouse_id = instance and instance.fbr_warehouse_id and instance.fbr_warehouse_id.id or False
        self.fbb_warehouse_id = instance and instance.fbb_warehouse_id and instance.fbb_warehouse_id.id or False
        self.bol_country_id = instance and instance.bol_country_id and instance.bol_country_id.id or False
        self.bol_lang_id = instance and instance.bol_lang_id and instance.bol_lang_id.id or False
        self.bol_order_prefix = instance and instance.bol_order_prefix or ''
        self.bol_stock_field = instance and instance.bol_stock_field and instance.bol_stock_field.id or False
        self.bol_pricelist_id = instance and instance.pricelist_id and instance.pricelist_id.id or False
        self.bol_payment_term_id = instance and instance.payment_term_id and instance.payment_term_id.id or False 
        self.bol_team_id=instance and instance.bol_team_id and instance.bol_team_id.id or False
        self.auto_create_product=instance and instance.auto_create_product
        self.bol_fulfillment_by = instance and instance.bol_fulfillment_by or False
        self.default_codition = instance and instance.default_codition or False
        self.default_delivery_code = instance and instance.default_delivery_code or False
        self.is_publish = instance and instance.is_publish or False
        self.sync_price_with_product = instance and instance.sync_price_with_product or False
        self.fbb_order_auto_import = instance and instance.fbb_order_auto_import or False
        self.fbr_order_auto_import = instance and instance.fbr_order_auto_import or False
        self.auto_update_stock = instance and instance.auto_update_stock or False
        self.fbr_order_workflow = instance and instance.fbr_order_workflow or False
        self.fbb_order_workflow = instance and instance.fbb_order_workflow or False
        self.import_shipment_order_type = instance and instance.import_shipment_order_type
        self.bol_manage_multi_tracking_number_in_delivery_order = instance and instance.bol_manage_multi_tracking_number_in_delivery_order
        self.auto_import_shipment=instance and instance.auto_import_shipment
        self.auto_retrive_shipment_status=instance and instance.auto_retrive_shipment_status
        self.bol_order_auto_update=instance and instance.bol_order_auto_update
        self.update_order_status_when_picking_in_ready=instance and instance.update_order_status_when_picking_in_ready
        self.validate_bol_stock_inventory = instance and instance.validate_bol_stock_inventory
        self.auto_import_fbb_inventory = instance and instance.auto_import_fbb_inventory
        self.allow_process_unshipped_bol_products = instance and instance.allow_process_unshipped_bol_products
        self.is_auto_start_return = instance and instance.is_auto_start_return
        self.bol_global_channel_id = instance and instance.global_channel_id and instance.global_channel_id.id or False
        try:
            fbb_order_import_cron_exist = instance and self.env.ref('bol_ept.ir_cron_import_bol_fbb_orders_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            fbb_order_import_cron_exist=False
        if fbb_order_import_cron_exist:
            self.fbb_order_import_interval_number=fbb_order_import_cron_exist.interval_number or False
            self.fbb_order_import_interval_type=fbb_order_import_cron_exist.interval_type or False
            self.fbb_order_import_next_execution=fbb_order_import_cron_exist.nextcall or False
            self.fbb_order_import_user_id=fbb_order_import_cron_exist.user_id.id or False 
        try:
            fbr_order_import_cron_exist = instance and self.env.ref('bol_ept.ir_cron_import_bol_fbr_orders_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            fbr_order_import_cron_exist=False
        if fbr_order_import_cron_exist:
            self.fbr_order_import_interval_number=fbr_order_import_cron_exist.interval_number or False
            self.fbr_order_import_interval_type=fbr_order_import_cron_exist.interval_type or False
            self.fbr_order_import_next_execution=fbr_order_import_cron_exist.nextcall or False
            self.fbr_order_import_user_id=fbr_order_import_cron_exist.user_id.id or False
        try:
            auto_update_cron_exist = instance and self.env.ref('bol_ept.ir_cron_update_bol_stock_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            auto_update_cron_exist=False
        if auto_update_cron_exist:
            self.update_stock_interval_number=auto_update_cron_exist.interval_number or False
            self.update_stock_interval_type=auto_update_cron_exist.interval_type or False
            self.update_stock_next_execution=auto_update_cron_exist.nextcall or False
            self.update_stock_user_id=auto_update_cron_exist.user_id.id or False
        try:
            auto_import_shipment_cron_exist = instance and self.env.ref('bol_ept.ir_cron_import_shipment_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            auto_import_shipment_cron_exist=False
        if auto_import_shipment_cron_exist:
            self.import_shipment_interval_number=auto_import_shipment_cron_exist.interval_number or False
            self.import_shipment_interval_type=auto_import_shipment_cron_exist.interval_type or False
            self.import_shipment_next_execution=auto_import_shipment_cron_exist.nextcall or False
            self.import_shipment_user_id=auto_import_shipment_cron_exist.user_id.id or False
        try:
            order_update_cron_exist = instance and self.env.ref('bol_ept.ir_cron_update_bol_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_update_cron_exist=False
        if order_update_cron_exist:
            self.bol_order_update_interval_number = order_update_cron_exist.interval_number or False
            self.bol_order_update_interval_type = order_update_cron_exist.interval_type or False
            self.bol_order_update_next_execution = order_update_cron_exist.nextcall or False
            self.bol_order_update_user_id = order_update_cron_exist.user_id.id or False
        try:
            retrive_shipment_status_cron_exist = instance and self.env.ref('bol_ept.ir_cron_retrive_shipment_status_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            retrive_shipment_status_cron_exist=False
        if retrive_shipment_status_cron_exist:
            self.retrive_shipment_status_interval_number = retrive_shipment_status_cron_exist.interval_number or False
            self.retrive_shipment_status_interval_type = retrive_shipment_status_cron_exist.interval_type or False
            self.retrive_shipment_status_next_execution = retrive_shipment_status_cron_exist.nextcall or False
            self.retrive_shipment_status_user_id = retrive_shipment_status_cron_exist.user_id.id or False
        try:
            import_fbb_inventory_cron_exist = instance and self.env.ref('bol_ept.ir_cron_import_fbb_inventory_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            import_fbb_inventory_cron_exist=False
        if import_fbb_inventory_cron_exist:
            self.import_fbb_inventory_interval_number = import_fbb_inventory_cron_exist.interval_number or False
            self.import_fbb_inventory_interval_type = import_fbb_inventory_cron_exist.interval_type or False
            self.import_fbb_inventory_next_execution = import_fbb_inventory_cron_exist.nextcall or False
            self.import_fbb_inventory_user_id = import_fbb_inventory_cron_exist.user_id.id or False 
        
    @api.multi
    def execute(self):
        instance = self.bol_instance_id
        values = {}
        res = super(ResConfigSettings,self).execute()
        if instance:
            values['company_id'] = self.bol_company_id and self.bol_company_id.id or False
            values['fbr_warehouse_id'] = self.fbr_warehouse_id and self.fbr_warehouse_id.id or False
            values['fbb_warehouse_id'] = self.fbb_warehouse_id and self.fbb_warehouse_id.id or False
            values['bol_country_id'] = self.bol_country_id and self.bol_country_id.id or False
            values['bol_lang_id'] = self.bol_lang_id and self.bol_lang_id.id or False
            values['bol_order_prefix'] = self.bol_order_prefix and self.bol_order_prefix
            values['bol_stock_field'] = self.bol_stock_field and self.bol_stock_field.id or False
            values['pricelist_id'] = self.bol_pricelist_id and self.bol_pricelist_id.id or False
            values['payment_term_id'] = self.bol_payment_term_id and self.bol_payment_term_id.id or False 
            values['bol_team_id'] = self.bol_team_id and self.bol_team_id.id or False
            values['auto_create_product'] = self.auto_create_product
            values['is_publish'] = self.is_publish
            values['bol_fulfillment_by'] = self.bol_fulfillment_by
            values['default_codition'] = self.default_codition
            values['default_delivery_code'] = self.default_delivery_code
            values['sync_price_with_product'] = self.sync_price_with_product
            values['fbb_order_auto_import']=self.fbb_order_auto_import
            values['fbr_order_auto_import']=self.fbr_order_auto_import
            values['auto_update_stock']=self.auto_update_stock
            values['fbr_order_workflow']=self.fbr_order_workflow and self.fbr_order_workflow.id or False
            values['fbb_order_workflow']=self.fbb_order_workflow and self.fbb_order_workflow.id or False
            values['import_shipment_order_type']=self.import_shipment_order_type
            values['bol_manage_multi_tracking_number_in_delivery_order']=self.bol_manage_multi_tracking_number_in_delivery_order
            values['auto_import_shipment']=self.auto_import_shipment
            values['bol_order_auto_update']=self.bol_order_auto_update
            values['auto_retrive_shipment_status']=self.auto_retrive_shipment_status
            values['update_order_status_when_picking_in_ready']=self.update_order_status_when_picking_in_ready
            values['validate_bol_stock_inventory']=self.validate_bol_stock_inventory
            values['auto_import_fbb_inventory']=self.auto_import_fbb_inventory
            values['allow_process_unshipped_bol_products']=self.allow_process_unshipped_bol_products
            values['is_auto_start_return']=self.is_auto_start_return
            values['global_channel_id']=self.bol_global_channel_id and self.bol_global_channel_id.id or False
            instance.write(values)
            self.setup_order_import_cron(instance)
            self.setup_update_stock_cron(instance)
            self.setup_import_shipment_cron(instance)
            self.setup_retrive_shipment_status_cron(instance)
            self.setup_order_status_update_cron(instance)
            self.setup_import_fbb_inventory_cron(instance)
        return res
    
    @api.multi   
    def setup_order_import_cron(self,instance):
        if self.fbb_order_auto_import:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_bol_fbb_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.fbb_order_import_interval_type](self.fbb_order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.fbb_order_import_interval_number,
                    'interval_type':self.fbb_order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_import_bol_fbb_sale_order_ept(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.fbb_order_import_user_id and self.fbb_order_import_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('bol_ept.ir_cron_import_bol_fbb_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_import_bol_fbb_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_bol_fbb_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        cron_exist=False
        if self.fbr_order_auto_import:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_bol_fbr_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.fbr_order_import_interval_type](self.fbr_order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.fbr_order_import_interval_number,
                    'interval_type':self.fbr_order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_import_bol_fbr_sale_order_ept(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.fbr_order_import_user_id and self.fbr_order_import_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('bol_ept.ir_cron_import_bol_fbr_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_import_bol_fbr_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_bol_fbr_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_update_stock_cron(self,instance):
        if self.auto_update_stock:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_update_bol_stock_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.update_stock_interval_type](self.update_stock_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.update_stock_interval_number,
                    'interval_type':self.update_stock_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_update_stock(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.update_stock_user_id and self.update_stock_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('bol_ept.ir_cron_update_bol_stock')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_update_bol_stock_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_update_bol_stock_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi
    def setup_import_shipment_cron(self,instance):
        if self.auto_import_shipment:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_shipment_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.update_stock_interval_type](self.update_stock_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.import_shipment_interval_number,
                    'interval_type':self.import_shipment_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_import_shipment(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.import_shipment_user_id and self.import_shipment_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('bol_ept.ir_cron_import_shipment')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_import_shipment_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_shipment_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_order_status_update_cron(self,instance):
        if self.bol_order_auto_update:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_update_bol_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.bol_order_update_interval_type](self.bol_order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.bol_order_update_interval_number,
                    'interval_type':self.bol_order_update_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_update_bol_order_status_ept(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.bol_order_update_user_id and self.bol_order_update_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('bol_ept.ir_cron_update_bol_order_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_update_bol_order_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_update_bol_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_retrive_shipment_status_cron(self,instance):
        if self.auto_retrive_shipment_status:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_retrive_shipment_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.retrive_shipment_status_interval_type](self.retrive_shipment_status_interval_number)
            vals = {'active' : True,
                    'interval_number':self.retrive_shipment_status_interval_number,
                    'interval_type':self.retrive_shipment_status_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_retrive_delivery_status_ept(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.retrive_shipment_status_user_id and self.retrive_shipment_status_user_id.id}
            if cron_exist:        
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('bol_ept.ir_cron_retrive_shipment_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_retrive_shipment_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_retrive_shipment_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_import_fbb_inventory_cron(self,instance):
        if self.auto_import_fbb_inventory:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_fbb_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.import_fbb_inventory_interval_type](self.import_fbb_inventory_interval_number)
            vals = {'active' : True,
                    'interval_number':self.import_fbb_inventory_interval_number,
                    'interval_type':self.import_fbb_inventory_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_import_fbb_inventory_ept(ctx={'bol_instance_id':%d})"%(instance.id),
                    'user_id': self.import_fbb_inventory_user_id and self.import_fbb_inventory_user_id.id}
            if cron_exist:        
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('bol_ept.ir_cron_import_fbb_inventory')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of Bol are deleted, please upgrade Bol Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'bol_ept',
                                                  'name':'ir_cron_import_fbb_inventory_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('bol_ept.ir_cron_import_fbb_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True