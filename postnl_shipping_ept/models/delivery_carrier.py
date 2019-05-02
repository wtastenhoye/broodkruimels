# Copyright (c) 2019 Emipro Technologies Pvt Ltd (www.emiprotechnologies.com). All rights reserved.
from odoo import models, fields, api, _
from requests import request
import time
import re
from odoo.exceptions import Warning
from odoo.addons.postnl_shipping_ept.models.postnl_response import Response
import binascii
import xml.etree.ElementTree as etree
import logging
_logger = logging.getLogger(__name__)

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"
    delivery_type = fields.Selection(selection_add=[('postnl_ept', 'PostNL')])
    delivery_type_postnl_ept = fields.Selection([('fixed_ept', 'PostNL Fixed Price'), ('base_on_rule_ept', 'PostNL Based on Rules')], string='PostNL Pricing',default='fixed_ept')
    postnl_product=fields.Selection([('3085', '3085-Standard shipment/ Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3385', '3385-Deliver to stated address only/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3090', '3090-Delivery to neighbour + Return when not home/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3390','3390-Deliver to stated address only + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3086', '3086-COD'),             
                        ('3091','3091-COD + Extra cover'),
                        ('3093','3093-COD + Return when not home'),
                        ('3097','3097-COD + Extra cover + Return when not home'),
                        ('3087','3087-Extra Cover/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3094','3087-Extra cover + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3089','3089-Signature on delivery + Deliver to stated address only/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3096','3096-Signature on delivery + Deliver to stated address only + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3189','3189-Signature on delivery/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3389','3389-Signature on delivery + Return when not home/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3533','3533-Pick up at PostNL location + Signature on Delivery'),
                        ('3534','3534-Pick up at  PostNL location + Extra Cover'),
                        ('3535','3535-Pick up at  PostNL location + COD'),
                        ('3536','3536-Pick up at  PostNL location + COD + Extra Cover'),
                        ('3543','3543-Early morning Pick up Points/Pick up at  PostNL location + Signature on Delivery + Notification'),
                        ('3544','3544-Early morning Pick up Points/Pick up at  PostNL location + Extra Cover + Notification'),
                        ('3545','3545-Early morning Pick up Points/Pick up at  PostNL location + COD + Notification'),
                        ('3546','3546-Early morning Pick up Points/Pick up at  PostNL location + COD + Extra Cover + Notification'),
                        ('2928','2928-Letterbox suit Extra NL(Pickup address)'),
                        ('3437','3437-Delivery to neighbour + Age Check'),
                        ('3438','3438-Standard shipment + Age Check'),
                        ('3443','3443-Extra Cover + Age Check'),
                        ('3446','3446-Extra Cover + Retun when not home + Age Check'),
                        ('3449','3449-Retun when not home + Age Check'),    
                        ('3440','3440-Standard shipment +  ID validation (based on date of birth)'),
                        ('3444','3444-Extra Cover +  ID validation (based on date of birth)'),
                        ('3447','3447-Extra Cover + Retun when not home + ID validation (based on date of birth)'),
                        ('3450','3450-Retun when not home +  ID validation (based on date of birth)'),
                        ('3442','3442-Standard shipment +  ID validation (based on ID number)'),
                        ('3445','3445-Extra Cover +  ID validation (based on ID number)'),
                        ('3448','3448-Extra Cover + Retun when not home + ID validation(based on ID number)'),
                        ('3451','3451-Retun when not home +  ID validation (based on ID number)'),
                        ('3571','3571-Pick up at PostNL location + Age Check'),
                        ('3572','3572-Retrieve at PostNL location + ID validation (based on date of birth)'),
                        ('3573','3573-Retrieve at PostNL location + ID validation (based on ID number)'),
                        ('3574','3574-Pick up at PostNL location + Age Check + Notification'),
                        ('3575','3575-Retrieve at PostNL location + ID validation (based on date of birth) + Notification'),
                        ('3576','3576-Retrieve at PostNL location + ID validation (based on ID number) + Notfication'),
                        ('3581','3581-Pick up at PostNL location + Extra Cover + Age Check'),
                        ('3582','3582-Retrieve at PostNL location + Extra Cover + ID validation (based on date of birth)'),
                        ('3583','3583-Retrieve at PostNL location + Extra Cover + ID validation (based on ID number)'),
                        ('3584','3584-Pick up at PostNL location + Extra Cover + Age Check + Notification'),
                        ('3585','3585-Retrieve at PostNL location + Extra Cover + ID validation (based on date of birth) + Notification'),
                        ('3586','3586-Retrieve at PostNL location + Extra Cover + ID validation (based on ID number) + Notification'),
                        ('1010','1010-Registered letter'),
                        ('1011','1011-Registered letter'),
                        ('1020','1020-Registered parcels Losse Post'),
                        ('1410','1410-Registered letters Partijen Post'),
                        ('1420','1420-Registered parcels Partijen Post'),
                        ('1175','1175-Letter + ID check'),
                        ('1178','1178-Letter + ID validation (based on date of birth)'),
                        ('1179','1179-Letter + age check'),
                        ('1180','1180-Letter + ID validation (based on ID number)'),
                        ('3083','3083-Food (dry and groceries)/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('3084','3084-Food (cool products)/ Evening delivery/Sameday delivery/Guaranteed/ Morning delivery'),
                        ('2285','2285-Single label variant/Business reply number'),
                        #belgium
                        ('4960','4960-Belgium Deliver to stated address only'),
                        ('4961','4961-Belgium Delivery to neighbour'),
                        ('4962','4962-Belgium Signature on delivery + Deliver to stated address only '),
                        ('4963','4963-Belgium Signature on delivery'),
                        ('4964','4964-Belgium COD + Return when not home'),
                        ('4965','4965-Belgium Extra cover (EUR 500) +  Deliver to stated address only'),
                        ('4966','4966-Belgium COD + Extra cover (EUR 500) + Return when not home'),
                        ('4924','4924-België Cash on Delivery'),
                        #Destination EU
                        ('4940','4940-EU Pack Special to business'),
                        ('4950','4950-EU Pack Special to business (Combilabel) '),
                        ('4944','4944-EU Pack Special to consumer'),
                        ('4952','4952-EU Pack Special to consumer (Combilabel)'),
                        ('3606','3606-AVG Pallet Pharma&Care 2-8 C /Guaranteed delivery Cargo/Cargo Pickup'),
                        ('3607','3607-AVG Pallet Pharma&Care 15-25 C /Guaranteed delivery Cargo/ Cargo Pickup'),
                        ('3608','3608-AVG Cargo Parcel Pharma&Care 2-8 C /Guaranteed delivery Cargo /Cargo Pickup'),
                        ('3609','3609-AVG Cargo Parcel Pharma&Care 15-25 C /Guaranteed delivery Cargo/ Cargo Pickup'),
                        ('3610','3610-AVG Pallet NL /Guaranteed delivery Cargo /Cargo Pickup'),
                        ('3611','3611-AVG Pallet NL + COD / Guaranteed delivery Cargo'),
                        ('3630','3630-AVG Parcel Plus NL / Guaranteed delivery Cargo/ Cargo Pickup'),
                        ('3631','3631-AVG Parcel Plus NL + COD / Guaranteed delivery Cargo'),
                        ('3657','3657-AVG Half Europallet NL / Guaranteed delivery Cargo /Cargo Pickup'),
                        ('3677','3677- AVG Half Europallet NL +COD / Guaranteed delivery Cargo'),
                        ('3696','3696-AVG Roll Cage container NL / Guaranteed delivery Cargo /Cargo Pickup'),
                        ('3618','3618-AVG Pallet BE /Cargo Pickup'),
                        ('3619','3619-AVG Pallet BE + COD'),
                        ('3638','3638-AVG Parcel Plus BE /Cargo Pickup'),
                        ('3639','3639-AVG Parcel Plus BE + COD'),
                        ('3658','3658-AVG Half Europallet BE /Cargo Pickup'),
                        ('3678','3678-AVG Half Europallet BE +COD'),
                        ('3697','3697-AVG Roll Cage container BE /Cargo Pickup'),
                        ('3622','3622-AVG Pallet LU/ Cargo Pickup'),
                        ('3623','3623-AVG Pallet LU + COD'),
                        ('3642','3642-AVG Parcel Plus LU /Cargo Pickup'),
                        ('3643','3643-AVG Parcel Plus LU + COD'),
                        ('3659','3659-AVG Half Europallet LU /Cargo Pickup'),
                        ('3679','3679-AVG Half Europallet LU +COD'),
                        ('3626','3626-AVG Euro Freight Pallet'),
                        ('3627','3627-AVG Euro Freight Parcel Plus'),
                        ('3628','3628-Extra@Home Top service 2 person delivery NL(Available destinations-NL)'),
                        ('3629','3629-Extra@Home Top service Btl 2 person delivery (Available destinations-BE;LU)'),
                        ('3653','3653-Extra@Home Top service 1 person delivery NL (Available destinations-NL)'),
                        ('3783','3783-Extra@Home Top service Btl 1 person delivery (Available destinations-BE;LU)'),
                        ('3790','3790-Extra@Home Drempelservice 1 person delivery NL (Available destinations-NL)'),
                        ('3791','3791-Extra@Home Drempelservice 2 person delivery NL'),
                        ('3792','3792-Extra@Home Drempelservice Btl 1 person delivery (Available destinations-BE;LU)'),
                        ('3793','3793-Extra@Home Drempelservice Btl 2 persons delivery (Available destinations-BE;LU)')],
                        string="Product Code Delivery",default='3085', help="Product code of the shipment, Each shipping product requires to be agreed upon in a contract between PostNL Pakketten and customers. The product codes mentioned must be used in various requests. The combilabel product codes are mapped to regular product codes.")
    barcode_type=fields.Selection([('3S/AB/00000000000-99999999999', '3S-(range(AB),serie(00000000000-99999999999)Length(15)(Dutch domestic shipments)'),
                        ('3S/ABCD/0000000-9999999', '3S-(range(ABCD),serie(0000000-9999999)Length(13)(Dutch domestic shipments)/(EPS shipments:)'),
                        ('3S/ABCD/987000000-987600000', '3S-(range(ABCD),serie(987000000-987600000)Length(15)(Dutch domestic shipments)'),
                        ('3S/ABC/10000000-20000000', '3S-(range(ABC),serie(10000000-20000000)(EPS shipments)'),
                        ('3S/A/5210500000-5210600000', '3S-(range(A),serie(5210500000-5210600000)(EPS shipments)'),
                        ('CC/1234/0000-9999', 'CC-(range(1234),serie(0000-9999)-GlobalPack shipments'),
                        ('CD/1112/0000-9999', 'CD-(range(1112),serie(0000-9999)-GlobalPack shipments'),
                        ('CP/1112/0000-9999','CP(range(1112),serie(0000-9999)-GlobalPack shipments')],
                        string="Type Of Barcode", help="type of Barcode , PostNL will provide you the exact barcode type to use with the PostNL Pakketten API ", default="3S/ABCD/0000000-9999999")
    product_combination=fields.Selection([('118/002','Early morning Pick up Points-characteristic 118, option 002'),
                                          ('002/014','ID check at the door(Age Check)- characteristic 002, option 014'),
                                          ('002/016','ID check at the door(based on date of birth)- characteristic 002, option 016'),
                                          ('002/012','ID check at the door(based on ID number)- characteristic 002, option 012'),
                                          ('152/025','Smart Returns- characteristic 152, option 025'),
                                          ('118/006','Evening delivery-characteristic 118, option 006'),
                                          ('101/008','Sunday delivery-characteristic 101, option 008'),
                                          ('118/015','Sameday delivery-characteristic 118, option 015'),
                                          ('118/006','Sameday delivery-characteristic 118, option 006'),
                                          ('118/017','Guaranteed/ Morning delivery-characteristic 118, option 017 (delivery before 09:00)'),
                                          ('118/007','Guaranteed/ Morning delivery-characteristic 118, option 007 (delivery before 10:00)'),
                                          ('118/008','Guaranteed/ Morning delivery- characteristic 118, option 008 (delivery before 12:00)'),
                                          ('118/012','Guaranteed/ Morning delivery-characteristic 118, option 012 (delivery before 17:00)'),
                                          ('118/007','Guaranteed delivery Cargo-118.007 for delivery before 10 am'),
                                          ('118/008','Guaranteed delivery Cargo-118.008 for delivery before 12 am'),
                                          ('118/013','Guaranteed delivery Cargo-118.013 for delivery before 14 pm'),
                                          ('135/001','Cargo Pickup- characteristic 135, option 001')],
                                          string="Product Combination", help="product characteristic and option(The characteristic of the ProductOption. Mandatory for some products, Please see the Products page   and The product option code for this ProductOption. Mandatory for some products, please see the Products page ")
    postnl_default_product_packaging_id = fields.Many2one('product.packaging', string="Default Package Type")
    is_cod=fields.Boolean(string="Is COD",help='select when use COD product')
    is_insured=fields.Boolean(string="Is Insured",help='select when use Insured product')
    is_pickup=fields.Boolean(string='Is Pick up address', help='select when use pickup address product')

    @api.onchange("delivery_type")
    def onchange_delivery_type(self):
        '''added by Emipro Technologies Pvt Ltd'''
        if self.delivery_type != 'postnl_ept':
            self.delivery_type_postnl_ept = ''
        else:
            self.delivery_type_postnl_ept = 'fixed_ept'
            
    @api.model
    def postnl_ept_rate_shipment(self, orders):
        """ Get the Rate of perticular shipping service for postnl
            @param orders
            @return: dict of default value of rate
            @author: Nimesh Jadav on dated 19-Jan-2019
        """
        if self.delivery_type_postnl_ept == 'fixed_ept':
            return self.fixed_rate_shipment(orders)
        if self.delivery_type_postnl_ept == 'base_on_rule_ept':
            return self.base_on_rule_rate_shipment(orders)
    
    @api.model
    def get_PostNL_url(self,url_data):
        """ Genrate the url of perticular shipping service
            @param : url data
            @return: Return URL Data
            @author: Emipro Technologies Pvt. Ltd.
        """
        if self.prod_environment:
            return "https://api.postnl.nl/shipment/%s"%(url_data)
        else:
            return "https://api-sandbox.postnl.nl/shipment/%s"%(url_data)
    
    @api.multi
    def body_request_for_postnl_barcode(self):
        """ Get the barcode Generation body for Postnl
            @param 
            @return: body of default value of Barcode generation
            @author: Nimesh Jadav 19 Jan 2019
        """
        root_node = etree.Element("Envelope")
        root_node.attrib['xmlns'] = "http://schemas.xmlsoap.org/soap/envelope/"
        body = etree.SubElement(root_node, "Body")
        #<body><GenerateBarcode>
        GenerateBarcode=etree.SubElement(body,"GenerateBarcode")
        GenerateBarcode.attrib['xmlns'] = "http://postnl.nl/cif/services/BarcodeWebService/"
        Message=etree.SubElement(GenerateBarcode,"Message")
        Message.attrib['xmlns'] = "http://postnl.nl/cif/domain/BarcodeWebService/"
        #ID of the message String [1-12]
        etree.SubElement(Message, "MessageID").text ='1'
        current_date = time.strftime('%d-%m-%Y %H:%M:%S')
        etree.SubElement(Message, "MessageTimeStamp").text ="%s" % (current_date)
        Customer=etree.SubElement(GenerateBarcode,"Customer")
        Customer.attrib['xmlns'] = "http://postnl.nl/cif/domain/BarcodeWebService/"
        etree.SubElement(Customer, "CustomerCode").text =self.shipping_instance_id and self.shipping_instance_id.postnl_customer_code or ''
        etree.SubElement(Customer, "CustomerNumber").text =self.shipping_instance_id and self.shipping_instance_id.postnl_customer_number or ''
        Barcode=etree.SubElement(GenerateBarcode,"Barcode")
        Barcode.attrib['xmlns'] = "http://postnl.nl/cif/domain/BarcodeWebService/"
        barcode_type=self.barcode_type.split('/')
        etree.SubElement(Barcode, "Type").text =barcode_type[0] or '3S'
        etree.SubElement(Barcode, "Range").text =self.shipping_instance_id and self.shipping_instance_id.postnl_customer_code or 'ABCD'
        etree.SubElement(Barcode, "Serie").text =barcode_type[2] or '100000-200000'
        return etree.tostring(root_node).decode('utf-8')

    @api.model
    def get_PostNL_barcode(self):
        """ Genrate the Barcode for Create Shipments.
            @param : 
            @return: Return Barcode 
            @author: Emipro Technologies Pvt. Ltd.
        """
        self.ensure_one()
        try:
            apikey=self.shipping_instance_id and self.shipping_instance_id.postnl_apikey
            headers = {"Content-Type": "text/xml; charset=utf-8","SOAPAction": "http://postnl.nl/cif/services/BarcodeWebService/IBarcodeWebService/GenerateBarcode",'APIKEY':apikey}
            body=self.body_request_for_postnl_barcode()
            _logger.info("PostNL barcode Requesting Data: %s" % (body))
            url = self.get_PostNL_url("v1_1/barcode/")
            response_body = request(method='POST', url=url, headers=headers,data=body)
            if response_body.status_code == 200:
                api = Response(response_body)
                results = api.dict()
                _logger.info("PostNL Barcode Response Data : %s" % (results))
                product_details=results.get('Envelope',{}).get('Body',{}) and results.get('Envelope',{}).get('Body',{}).get('GenerateBarcodeResponse',{}) or False
                barcode=product_details and product_details.get('Barcode',{}) or False
                if barcode:
                    return barcode
            else:
                    raise Warning(response_body.text)
        except Exception as e:
                raise Warning(e)
    
    @api.multi
    def body_request_for_postnl_send_shipping(self,picking):
        """ Get the send shipping body for Postnl
            @param 
            @return: body of default value of shipping
            @author: Nimesh Jadav 19 Jan 2019
        """
        picking_partner_id = picking.partner_id
        picking_company_id = picking.picking_type_id and picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.partner_id
        total_bulk_weight = self.convert_weight(picking.weight_uom_id, self.weight_uom_id, picking.weight_bulk)
        total_bulk_weight=int(total_bulk_weight)
        root_node = etree.Element("Envelope")
        root_node.attrib['xmlns'] = "http://schemas.xmlsoap.org/soap/envelope/"
        body = etree.SubElement(root_node, "Body")
        #<body><GenerateLabel>
        GenerateLabel=etree.SubElement(body,"GenerateLabel")
        GenerateLabel.attrib['xmlns'] = "http://postnl.nl/cif/services/LabellingWebService/"
        Customer=etree.SubElement(GenerateLabel,"Customer")
        Customer.attrib['xmlns'] = "http://postnl.nl/cif/domain/LabellingWebService/"
        #Address type is 02=Sender
        Address=etree.SubElement(Customer,"Address")
        etree.SubElement(Address, "AddressType").text ='02'
        etree.SubElement(Address, "City").text = picking_company_id.city or ''
        etree.SubElement(Address, "CompanyName").text = picking_company_id.name or ''
        etree.SubElement(Address, "Countrycode").text = picking_company_id.country_id and picking_company_id.country_id.code or ''
        etree.SubElement(Address, "Name").text = picking_company_id.name or ''
        house_number = re.search(r'\d{1,5}', picking_company_id.street)
        house_number = str(house_number.group()) if house_number else ""
        etree.SubElement(Address, "HouseNr").text =house_number or ''
        address_line1 = picking_company_id.street or ""
        etree.SubElement(Address, "Street").text ="%s %s" % (
        address_line1.replace(house_number, ''), picking_company_id.street2) if picking_company_id.street2 else address_line1.replace(house_number, '')
        etree.SubElement(Address, "Zipcode").text = picking_company_id.zip or ''
        etree.SubElement(Customer, "CollectionLocation").text =picking_company_id.zip or ''
        etree.SubElement(Customer, "ContactPerson").text =picking_company_id.name or ''
        etree.SubElement(Customer, "CustomerCode").text =self.shipping_instance_id and self.shipping_instance_id.postnl_customer_code or ''
        etree.SubElement(Customer, "CustomerNumber").text =self.shipping_instance_id and self.shipping_instance_id.postnl_customer_number or ''
        etree.SubElement(Customer, "Email").text =picking_company_id.email or ''
        Message=etree.SubElement(GenerateLabel,"Message")
        Message.attrib['xmlns'] = "http://postnl.nl/cif/domain/LabellingWebService/"
        #ID of the message String [1-12]
        etree.SubElement(Message, "MessageID").text ='01'
        current_date = time.strftime('%d-%m-%Y %H:%M:%S')
        etree.SubElement(Message, "MessageTimeStamp").text ="%s" % (current_date)
        etree.SubElement(Message, "Printertype").text ='GraphicFile|PDF'
        Shipments=etree.SubElement(GenerateLabel,"Shipments")
        Shipments.attrib['xmlns'] = "http://postnl.nl/cif/domain/LabellingWebService/"
        for package_id in picking.package_ids:
            product_weight = self.convert_weight(picking.weight_uom_id, self.weight_uom_id, package_id.shipping_weight)
            product_weight=int(product_weight)
            total_value = sum([(line.qty_done* line.product_id.list_price) if line.result_package_id==package_id else 0 for line in picking.move_line_ids])
            self.request_for_shipment_body_PostNL(Shipments, product_weight, picking_partner_id,picking_company_id,total_value)
        if total_bulk_weight:
            total_value = sum([(line.qty_done* line.product_id.list_price) if not line.result_package_id else 0 for line in picking.move_line_ids])
            self.request_for_shipment_body_PostNL(Shipments,total_bulk_weight, picking_partner_id,picking_company_id,total_value)
        return etree.tostring(root_node).decode('utf-8')

    @api.multi
    def request_for_shipment_body_PostNL(self,Shipments,product_weight,picking_partner_id,picking_company_id,total_value):
        """ Prepare Shipment body parameter
            @param shipment parameter details
            @return: Body of shipment
            @author: Nimesh Jadav 19 Jan 2019
        """
        #<body><GenerateLabel><Shipments><Shipment>
        Shipment=etree.SubElement(Shipments,"Shipment")
        Addresses=etree.SubElement(Shipment,"Addresses")
        Address=etree.SubElement(Addresses,"Address")
        #Within the CustomerType, only AddressType 02 can be used. This Type can also be placed in the ShipmentType. Within the ShipmentType, at least ShipmentType with 01 is required.
        #Address type is 01=Receiver  
        etree.SubElement(Address, "AddressType").text ='01'
        etree.SubElement(Address, "City").text = picking_partner_id.city or ''
        etree.SubElement(Address, "Countrycode").text = picking_partner_id.country_id and picking_partner_id.country_id.code or ''
        etree.SubElement(Address, "Name").text = picking_partner_id.name or ''
        house_number = re.search(r'\d{1,5}', picking_partner_id.street)
        house_number = str(house_number.group()) if house_number else ""
        etree.SubElement(Address, "HouseNr").text =house_number or ''
        address_line1 = picking_partner_id.street or ""
        etree.SubElement(Address, "Street").text ="%s %s" % (
        address_line1.replace(house_number, ''), picking_partner_id.street2) if picking_partner_id.street2 else address_line1.replace(house_number, '')
        etree.SubElement(Address, "Zipcode").text =picking_partner_id.zip or ''
        if self.is_pickup:
            Address=etree.SubElement(Addresses,"Address")
            #Address type is 09=Delivery address (for use with Pick up at PostNL location)
            etree.SubElement(Address, "AddressType").text = '09'
            etree.SubElement(Address, "City").text = picking_partner_id.city or ''
            etree.SubElement(Address, "CompanyName").text = picking_partner_id.name or ''
            etree.SubElement(Address, "Countrycode").text = picking_partner_id.country_id and picking_partner_id.country_id.code or ''
            etree.SubElement(Address, "Name").text = picking_partner_id.name or ''
            house_number = re.search(r'\d{1,5}', picking_partner_id.street)
            house_number = str(house_number.group()) if house_number else ""
            etree.SubElement(Address, "HouseNr").text =house_number or ''
            address_line1 = picking_partner_id.street or ""
            etree.SubElement(Address, "Street").text ="%s %s" % (
            address_line1.replace(house_number, ''), picking_partner_id.street2) if picking_partner_id.street2 else address_line1.replace(house_number, '')
            etree.SubElement(Address, "Zipcode").text = picking_partner_id.zip or ''
        Amounts=etree.SubElement(Shipment,"Amounts")
        if self.is_cod:
            Amount=etree.SubElement(Amounts,"Amount")        
            etree.SubElement(Amount, "AccountName").text =picking_partner_id.name or ''
            etree.SubElement(Amount, "AmountType").text ='01'
            etree.SubElement(Amount, "Currency").text =picking_company_id.currency_id and picking_company_id.currency_id.name or ''
            etree.SubElement(Amount, "IBAN").text =picking_partner_id.postnl_iban_number or ''
            etree.SubElement(Amount, "Value").text ="%s" % (total_value or '')
        if self.is_insured:
            Amount=etree.SubElement(Amounts,"Amount")        
            etree.SubElement(Amount, "AccountName").text =picking_partner_id.name or ''
            etree.SubElement(Amount, "AmountType").text ='02'
            etree.SubElement(Amount, "Currency").text =picking_company_id.currency_id and picking_company_id.currency_id.name or ''
            etree.SubElement(Amount, "IBAN").text =picking_partner_id.postnl_iban_number or ''
            etree.SubElement(Amount, "Value").text ="%s" % (total_value or '')
        barcode=self.get_PostNL_barcode()
        etree.SubElement(Shipment, "Barcode").text = "%s" % (barcode or '')
        Contacts=etree.SubElement(Shipment,"Contacts")
        Contact=etree.SubElement(Contacts,"Contact")
        #01=Receiver 02=Sender
        etree.SubElement(Contact, "ContactType").text ='01'
        etree.SubElement(Contact, "Email").text =picking_partner_id.email or ''
        etree.SubElement(Contact, "SMSNr").text =picking_partner_id.phone or ''
        current_date = time.strftime('%d-%m-%Y %H:%M:%S')
        etree.SubElement(Shipment, "DeliveryDate").text = current_date or ''
        Dimension=etree.SubElement(Shipment,"Dimension")
        etree.SubElement(Dimension,'Length').text= "%s" % (self.postnl_default_product_packaging_id and self.postnl_default_product_packaging_id.length or "0")
        etree.SubElement(Dimension,'Width').text= "%s" % (self.postnl_default_product_packaging_id and self.postnl_default_product_packaging_id.width or "0")
        etree.SubElement(Dimension,'Height').text="%s" % (self.postnl_default_product_packaging_id and self.postnl_default_product_packaging_id.height or "0")
        etree.SubElement(Dimension,'Volume').text='cm'
        etree.SubElement(Dimension,'Weight').text="%s" % (product_weight or '')
        etree.SubElement(Shipment,'ProductCodeDelivery').text=self.postnl_product or ''
        if self.product_combination:
            ProductOptions=etree.SubElement(Shipment,"ProductOptions")
            ProductOption=etree.SubElement(ProductOptions,"ProductOption")
            product_combination=self.product_combination.split('/')
            etree.SubElement(ProductOption,'Characteristic').text="%s" % (product_combination[0] if product_combination[0] else '')
            etree.SubElement(ProductOption,'Option').text="%s" % (product_combination[1] if product_combination[1] else '')
        return etree.tostring(Shipments).decode('utf-8')

    @api.model
    def postnl_ept_send_shipping(self, pickings):
        """Create Shipping for PostNL and Generate Label
            @param: pickings
            @return: Shipping id for label print
            @author: Nimesh A Jadav on dated 24-Nov-2018
        """
        self.ensure_one()
        for picking in pickings:
            try:
                apikey=self.shipping_instance_id and self.shipping_instance_id.postnl_apikey
                headers = {"Content-Type": "text/xml; charset=utf-8","SOAPAction": "http://postnl.nl/cif/services/LabellingWebService/ILabellingWebService/GenerateLabel",'APIKEY':apikey}
                body=self.body_request_for_postnl_send_shipping(picking)
                _logger.info("PostNL Shipment Requesting Data: %s" % (body))
                url = self.get_PostNL_url("v2_2/label/")
                response_body = request(method='POST', url=url, headers=headers,data=body)
                if response_body.status_code == 200:
                    api = Response(response_body)
                    results = api.dict()
                    _logger.info("PostNL Generatelabel Response Data : %s" % (results))
                    ResponseShipments=results.get('Envelope',{}).get('Body',{}) and results.get('Envelope',{}).get('Body',{}).get('GenerateLabelResponse',{}) and results.get('Envelope',{}).get('Body',{}).get('GenerateLabelResponse',{}).get("ResponseShipments",{}) and results.get('Envelope',{}).get('Body',{}).get('GenerateLabelResponse',{}).get("ResponseShipments",{}).get('ResponseShipment',{}) or False
                    final_tracking_no = []
                    if isinstance(ResponseShipments, dict):
                        ResponseShipments = [ResponseShipments]
                    for ResponseShipment in ResponseShipments:
                        barcode=ResponseShipment.get('Barcode',{}) or False
                        final_tracking_no.append(barcode)
                        labels=ResponseShipment.get('Labels',{}) and ResponseShipment.get('Labels',{}).get('Label',{}) or False
                        if isinstance(labels, dict):
                            labels = [labels]
                        for label in labels:
                            label_detail=label.get("Content",{})
                            form_binary_data = binascii.a2b_base64(str(label_detail))
                            mesage_ept = (_("Shipment created!<br /> <b>Shipment Tracking Number : </b>%s") % (barcode))
                            picking.message_post(body=mesage_ept, attachments=[('PostNL Label Form_%s.pdf' % (barcode), form_binary_data )])
                        shipping_data = {'exact_price': 0.0,'tracking_number':','.join(final_tracking_no)}
                        response=[shipping_data]
                    return response
                else:
                    raise Warning(response_body.text)
            except Exception as e:
                raise Warning(e)
    
    @api.multi
    def postnl_ept_get_tracking_link(self, picking):
        """ Tracking the shipment from PostNL
            @param: picking
            @return: Redirect PostNL site and tracking the shippment.
            @author: Nimesh A Jadav
        """
        link = picking.carrier_id and picking.carrier_id.shipping_instance_id and picking.carrier_id.shipping_instance_id.tracking_link or 'https://www.internationalparceltracking.com/#/search?barcode='
        res = '%s%s' % (link, picking.carrier_tracking_ref)
        return res
    
    @api.multi
    def postnl_ept_cancel_shipment(self, picking):
        raise Warning(_("Can Not Possible To Cancel PostNL Shipment!"))