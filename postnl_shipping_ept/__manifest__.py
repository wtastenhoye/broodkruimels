# -*- coding: utf-8 -*-pack
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    # App information
    'name': 'PostNL Odoo Shipping Connector',
    'category': 'Website',
    'version': '12.0',
    'summary': 'PostNL Odoo Shipping Integration integrates your PostNL account with Odoo seamlessly to manage all the shipping operations from single window and hassle-free.',
    'license': 'OPL-1',
    

    # Dependencies
    'depends': ['shipping_integration_ept'],
    
    #views
    'data': ['views/view_shipping_instance_ept.xml',
             'views/delivery_carrier_view.xml',
             'views/res_partner_ept_view.xml'],
             
    # Odoo Store Specific
    'images': ['static/description/post-NL-cover.jpg'],

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    
    # Technical
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'live_test_url': 'https://www.emiprotechnologies.com/free-trial?app=postnl-shipping-ept&version=12',
    'price': '149',
    'currency': 'EUR',
}
