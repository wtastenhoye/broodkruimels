{
   
   # App information
   
    'name': 'Odoo bol.com connector',
    'version': '11.0',
    'category': 'Sales',
    'license': 'OPL-1',
    'summary': """Odoo bol.com integration helps to manage key operations of bol.com efficiently from Odoo.""",
    
   
   
    # Author

    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
       
       
    # Dependencies
    
    
    
    'depends': ['sale_stock', 'auto_invoice_workflow_ept', 'common_connector_library', 'delivery', 'document'],
    'external_dependencies':{"python" : ["enum"]},
    
    # Views
    
    'data': [   
                'security/group.xml',
                'views/stock_warehouse_view.xml',
                'views/bol_instance_main_menu.xml',
                'wizard/bol_process_import_export.xml',
                'views/bol_process_log_book.xml',
                'views/bol_product_ept_view.xml',
                'views/bol_product_status_view.xml',
                'views/bol_fbb_transport_view.xml',
                'views/bol_fbr_transport_view.xml',
                'views/bol_delivery_window_view.xml',
                'views/bol_inbound_ept_view.xml',
                'views/sale_workflow_config.xml',
                'views/sale_order_view.xml',
                'views/res_partner_view.xml',
                'views/stock_picking_view.xml',
                'views/stock_view.xml',
                'views/stock_inventory_view.xml',
                'views/return_handle_view.xml',
                'wizard/res_config_view.xml',
                'views/ir_cron.xml',
                'wizard/product_label_format_view.xml',
                'security/ir.model.access.csv',
                'data/bol.fbr.transport.ept.csv',
                'views/web_templates.xml',
                'views/bol_instance_ept_view.xml',
            ],
            
            
	  # Odoo Store Specific
    
    'images': ['static/description/bol.com-odoo-cover.jpg'],      
  
  
    # Technical 
    
    'installable': True,
    'currency': 'EUR',
    'price': 529.00,
    'live_test_url':'http://www.emiprotechnologies.com/free-trial?app=bol-ept&version=11',
    'auto_install': False,
    'application': True,
          
	 
}
