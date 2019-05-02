from odoo import models,fields,api,_
from odoo.exceptions import Warning
from .. import woocommerce
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class woo_instance_config(models.TransientModel):
    _name = 'res.config.woo.instance'
    _description = "WooCommerce Instance"
    
    name = fields.Char("Instance Name")
    consumer_key=fields.Char("Consumer Key",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")
    consumer_secret=fields.Char("Consumer Secret",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")    
    host=fields.Char("Host",required=True)
    verify_ssl=fields.Boolean("Verify SSL",default=False,help="Check this if your WooCommerce site is using SSL certificate")
    country_id = fields.Many2one('res.country',string = "Country",required=True)
    is_image_url = fields.Boolean("Is Image URL?",help="Check this if you use Images from URL\nKepp as it is if you use Product images")
    admin_username=fields.Char("Username", help="WooCommerce UserName,Used to Export Image Files.")
    admin_password=fields.Char("Password", help="WooCommerce Password,Used to Export Image Files.")
    woo_version = fields.Selection([('new','2.6+'),('old','<=2.6')],default='old',string="WooCommerce Version",help="Set the appropriate WooCommerce Version you are using currently or\nLogin into WooCommerce site,Go to Admin Panel >> Plugins")    
    is_latest=fields.Boolean('3.0 or later',default=False)
    auto_active_currency = fields.Boolean("Auto Active Currency", default=True,
                                          help="Automatically changes currency state to active if it is inactive.")  # Auto Active Currency Field Added By : Ajay Ghimre on 12 Nov 2018.

    @api.constrains('host')
    def woo_host_constrains(self):
        if self.host and self.host.strip()[-1] == '/':
            raise Warning(
                "Host should not end with character '/'.\nPlease Remove it from the end of host string and try again.")

    @api.onchange('host')
    def onchange_host(self):
        if self.host and 'https' in self.host:
            self.verify_ssl = True
        else:
            self.verify_ssl = False
    
    @api.multi
    def test_woo_connection(self):
        host = self.host
        consumer_key = self.consumer_key
        consumer_secret = self.consumer_secret
        wp_api = True if self.woo_version == 'new' else False
        version = "wc/v1" if wp_api else "v3"
        if self.is_latest:
            version = "wc/v2"
        wcapi = woocommerce.api.API(url=host, consumer_key=consumer_key,
                    consumer_secret=consumer_secret,verify_ssl=self.verify_ssl,wp_api=wp_api,version=version,query_string_auth=True)        
        r = wcapi.get("products")
        if not isinstance(r,requests.models.Response):
            raise Warning(_("Response is not in proper format :: %s"%(r)))
        if r.status_code != 200:
            raise Warning(_("%s\n%s"%(r.status_code,r.reason)))
        else:    
            instance=self.env['woo.instance.ept'].create({'name':self.name,
                                                 'consumer_key':self.consumer_key,                                                 
                                                 'consumer_secret':self.consumer_secret,                                                 
                                                 'host':self.host,
                                                 'verify_ssl':self.verify_ssl,
                                                 'country_id':self.country_id.id,
                                                 'company_id':self.env.user.company_id.id,
                                                 'is_image_url':self.is_image_url,
                                                 'woo_version':self.woo_version,
                                                 'is_latest':self.is_latest,
                                                 'admin_username':self.admin_username,
                                                 'admin_password':self.admin_password,
                                                 'auto_active_currency': self.auto_active_currency,
                                                 })        
            if instance.is_latest:
                self.env['woo.payment.gateway'].get_payment_gateway(instance)
        return True
    
class woo_config_settings(models.TransientModel):
    _name = 'woo.config.settings'
    _inherit = 'res.config.settings'
    
    @api.model
    def create(self, vals):
        if not vals.get('company_id'):
            vals.update({'company_id': self.env.user.company_id.id})
        res = super(woo_config_settings, self).create(vals)
        return res
    
    @api.model
    def _default_instance(self):
        instances = self.env['woo.instance.ept'].search([])
        return instances and instances[0].id or False
       
    @api.model
    def _get_default_company(self):
        company_id = self.env.user._get_company()
        if not company_id:
            raise Warning(_('There is no default company for the current user!'))
        return company_id
        
    woo_instance_id = fields.Many2one('woo.instance.ept', 'Woo Instance', default=_default_instance,help="Select WooCommerce Instance that you want to configure.")
    warehouse_id = fields.Many2one('stock.warehouse',string = "Woo Instance Warehouse",help="Stock Management, Order Processing & Fulfillment will be carried out from this warehouse.")
    company_id = fields.Many2one('res.company',string='Company',default=_get_default_company,help="Orders and Invoices will be generated of this company.")
    country_id = fields.Many2one('res.country',string = "Woo Instance Country")
    lang_id = fields.Many2one('res.lang', string='Instance Language',help="Select language for WooCommerce customer.")
    # Added by jigneshb
    use_custom_order_prefix = fields.Boolean(string="Use Custom Order Prefix",
                                             help="True:Use Custom Order Prefix, False:Default Sale Order Prefix")
    order_prefix = fields.Char(size=10, string='Woo Order Prefix')
    import_order_status_ids = fields.Many2many('import.order.status','woo_config_settings_order_status_rel','woo_config_id','status_id',"Import Order Status",help="Select Order Status of the type of orders you want to import from WooCommerce.")     

    stock_field = fields.Many2one('ir.model.fields', string='Stock Field',help="Choose if you want to update stock to WooCommerce based on Quantity on Hand or Forecasted Quantity (Onhand - Outgoing).")
    
    pricelist_id = fields.Many2one('product.pricelist', string='Woo Instance Pricelist',help="Product Price will be calculated in Odoo based on this pricelist.")
    payment_term_id = fields.Many2one('account.payment.term', string='Woo Instance Payment Term',help="Select the condition of payment for invoice.")
    woo_team_id=fields.Many2one('crm.team', 'Woo Sales Team',help="Choose Sales Team that handles the order you import.", oldname='section_id')
    woo_global_channel_id = fields.Many2one('global.channel.ept',string = "Woo Global Channel")

    discount_product_id=fields.Many2one("product.product","Woo Discount",domain=[('type','=','service')],required=False,help="Discount provided via coupon codes for promotional offers.")
    fee_line_id=fields.Many2one("product.product","Fees",domain=[('type','=','service')],required=False,help="Any Extra fees applicable under specific condition(s) (e.g., Extra $20 if payment method is COD).")

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Woo Fiscal Position')
       
    order_auto_import = fields.Boolean(string='Auto Order Import?',help="Check if you want to automatically import orders at certain interval.")
    order_import_interval_number = fields.Integer('Woo Import Order Interval Number',help="Repeat every x.",default=10)
    order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Woo Import Order Interval Unit')
    order_import_next_execution = fields.Datetime('Order Import Next Execution', help='Next execution time of order Import')
    order_import_user_id = fields.Many2one('res.users',string="Order Import User",help='User',default=lambda self: self.env.user)
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?")
    
    order_auto_update=fields.Boolean(string="Auto Order Update ?",help="Check if you want to automatically update order status to WooCommerce.")
    order_update_interval_number = fields.Integer('Woo Update Order Interval Number',help="Repeat every x.",default=10)
    order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Woo Update Order Interval Unit')
    order_update_next_execution = fields.Datetime('Order Update Next Execution', help='Next execution time of Order Update')    
    order_update_user_id = fields.Many2one('res.users',string="Order Update User",help='User',default=lambda self: self.env.user)
    
    stock_auto_export=fields.Boolean('Stock Auto Update.', default=False,help="Check if you want to automatically update stock levels from Odoo to WooCommerce.")
    update_stock_interval_number = fields.Integer('Update Stock Interval Number',help="Repeat every x.",default=10)
    update_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Stock Interval Unit')
    update_stock_next_execution = fields.Datetime('Update Stock Next Execution', help='Next execution time')    
    update_stock_user_id = fields.Many2one('res.users',string="Woo User",help='Woo Stock Update User',default=lambda self: self.env.user)
    
    is_set_price = fields.Boolean(string="Set Price ?",default=False)
    is_set_stock = fields.Boolean(string="Set Stock ?",default=False)
    is_publish = fields.Boolean(string="Publish In Website ?",default=False)
    is_set_image = fields.Boolean(string="Set Image ?",default=False)    
    sync_images_with_product=fields.Boolean("Sync/Import Images?",help="Check if you want to import images along with products",default=False)
    sync_price_with_product=fields.Boolean("Sync/Import Product Price?",help="Check if you want to import price along with products",default=False)
    is_show_debug_info=fields.Boolean('Show Debug Information?',default=False)

    # Added by jigneshb
    @api.onchange('use_custom_order_prefix')
    def onchange_custom_order_prefix(self):
        if not self.use_custom_order_prefix:
            self.order_prefix = ''

    @api.onchange('woo_instance_id')
    def onchange_woo_instance_id(self):
        instance = self.woo_instance_id or False
        self.company_id=instance and instance.company_id and instance.company_id.id or False
        self.warehouse_id = instance and instance.warehouse_id and instance.warehouse_id.id or False
        self.country_id = instance and instance.country_id and instance.country_id.id or False
        self.lang_id = instance and instance.lang_id and instance.lang_id.id or False
        self.use_custom_order_prefix = instance and instance.use_custom_order_prefix or False
        self.order_prefix = instance and instance.order_prefix or ''
        self.import_order_status_ids = instance and instance.import_order_status_ids.ids
        self.stock_field = instance and instance.stock_field and instance.stock_field.id or False
        self.pricelist_id = instance and instance.pricelist_id and instance.pricelist_id.id or False
        self.payment_term_id = instance and instance.payment_term_id and instance.payment_term_id.id or False 
        self.fiscal_position_id = instance and instance.fiscal_position_id and instance.fiscal_position_id.id or False
        self.discount_product_id=instance and instance.discount_product_id and instance.discount_product_id.id or False
        self.fee_line_id=instance and instance.fee_line_id and instance.fee_line_id.id or False        
        self.order_auto_import=instance and instance.order_auto_import
        self.stock_auto_export=instance and instance.stock_auto_export        
        self.order_auto_update=instance and instance.order_auto_update
        self.woo_team_id=instance and instance.section_id and instance.section_id.id or False
        self.auto_import_product=instance and instance.auto_import_product
        self.is_set_price = instance and instance.is_set_price or False
        self.is_set_stock = instance and instance.is_set_stock or False
        self.is_publish = instance and instance.is_publish or False
        self.is_set_image = instance and instance.is_set_image or False
        self.sync_images_with_product = instance and instance.sync_images_with_product or False
        self.sync_price_with_product = instance and instance.sync_price_with_product or False
        self.is_show_debug_info = instance and instance.is_show_debug_info or False
        self.woo_global_channel_id = instance and instance.global_channel_id or False
        
        try:
            inventory_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            inventory_cron_exist=False
        if inventory_cron_exist:
            self.update_stock_interval_number=inventory_cron_exist.interval_number or False
            self.update_stock_interval_type=inventory_cron_exist.interval_type or False
            self.update_stock_next_execution = inventory_cron_exist.nextcall or False
            self.update_stock_user_id = inventory_cron_exist.user_id.id or False 
        try:
            order_import_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_import_cron_exist=False
        if order_import_cron_exist:
            self.order_import_interval_number = order_import_cron_exist.interval_number or False
            self.order_import_interval_type = order_import_cron_exist.interval_type or False
            self.order_import_next_execution = order_import_cron_exist.nextcall or False
            self.order_import_user_id = order_import_cron_exist.user_id.id or False
        try:
            order_update_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_update_cron_exist=False
        if order_update_cron_exist:
            self.order_update_interval_number = order_update_cron_exist.interval_number or False
            self.order_update_interval_type = order_update_cron_exist.interval_type or False
            self.order_update_next_execution = order_update_cron_exist.nextcall or False
            self.order_update_user_id = order_update_cron_exist.user_id.id or False
    
    @api.multi
    def execute(self):
        instance = self.woo_instance_id
        values = {}
        res = super(woo_config_settings,self).execute()
        if instance:
            values['company_id'] = self.company_id and self.company_id.id or False
            values['warehouse_id'] = self.warehouse_id and self.warehouse_id.id or False
            values['country_id'] = self.country_id and self.country_id.id or False
            values['lang_id'] = self.lang_id and self.lang_id.id or False
            values['use_custom_order_prefix'] = self.use_custom_order_prefix or False
            values['order_prefix'] = self.order_prefix or ''
            values['import_order_status_ids'] = [(6,0,self.import_order_status_ids.ids)]           
            values['stock_field'] = self.stock_field and self.stock_field.id or False
            values['pricelist_id'] = self.pricelist_id and self.pricelist_id.id or False
            values['payment_term_id'] = self.payment_term_id and self.payment_term_id.id or False 
            values['fiscal_position_id'] = self.fiscal_position_id and self.fiscal_position_id.id or False
            values['discount_product_id']=self.discount_product_id.id or False
            values['fee_line_id']=self.fee_line_id.id or False            
            values['order_auto_import']=self.order_auto_import
            values['stock_auto_export']=self.stock_auto_export            
            values['order_auto_update']=self.order_auto_update
            values['section_id']=self.woo_team_id and self.woo_team_id.id or False
            values['auto_import_product']=self.auto_import_product
            values['is_set_price']=self.is_set_price or False
            values['is_set_stock']=self.is_set_stock or False
            values['is_publish']=self.is_publish or False
            values['is_set_image']=self.is_set_image or False
            values['sync_images_with_product']=self.sync_images_with_product or False
            values['sync_price_with_product']=self.sync_price_with_product or False
            values['is_show_debug_info']=self.is_show_debug_info or False
            values['global_channel_id']=self.woo_global_channel_id and self.woo_global_channel_id.id or False
            instance.write(values)
            self.setup_order_import_cron(instance)
            self.setup_order_status_update_cron(instance)                             
            self.setup_update_stock_cron(instance)                 

        return res

    @api.multi   
    def setup_order_import_cron(self,instance):
        if self.order_auto_import:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_import_interval_type](self.order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.order_import_interval_number,
                    'interval_type':self.order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_import_woo_sale_order_ept(ctx={'woo_instance_id':%d})"%(instance.id),
                    'user_id': self.order_import_user_id and self.order_import_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_import_woo_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True        
    
    @api.multi   
    def setup_order_status_update_cron(self,instance):
        if self.order_auto_update:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_update_interval_type](self.order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.order_update_interval_number,
                    'interval_type':self.order_update_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_update_woo_order_status_ept(ctx={'woo_instance_id':%d})"%(instance.id),
                    'user_id': self.order_update_user_id and self.order_update_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_update_woo_order_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_update_stock_cron(self,instance):
        if self.stock_auto_export:
            try:                
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.update_stock_interval_type](self.update_stock_interval_number)
            vals = {'active' : True,
                    'interval_number':self.update_stock_interval_number,
                    'interval_type':self.update_stock_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'code':"model.auto_update_stock_ept(ctx={'woo_instance_id':%d})"%(instance.id),
                    'user_id': self.update_stock_user_id and self.update_stock_user_id.id}
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:                    
                    update_stock_cron = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock')
                except:
                    update_stock_cron=False
                if not update_stock_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_stock_cron.name
                vals.update({'name':name})
                new_cron = update_stock_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_update_woo_stock_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})        
        return True
