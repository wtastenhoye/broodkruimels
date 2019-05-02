# Copyright (c) 2019 Emipro Technologies Pvt Ltd (www.emiprotechnologies.com). All rights reserved.
from odoo import models, fields, api, _

class ShippingInstanceEpt(models.Model):
    _inherit = "shipping.instance.ept"
    provider = fields.Selection(selection_add=[('postnl_ept', 'PostNL')])
    postnl_customer_code = fields.Char("Customer Code", copy=False, help="Customer code as known at PostNL Pakketten  Example:'ABCD'")
    postnl_customer_number=fields.Char("Customer Number", copy=False, help="Customer number as known at PostNL Pakketten    Example:'11223344' ")
    postnl_apikey=fields.Char("APIKEY",help="APIKEY Provided by postnl")
    _sql_constraints = [('user_unique', 'unique(postnl_customer_number)', 'User already exists.')]
    
    @api.one
    def postnl_ept_retrive_shipping_services(self, to_add):
        """ Retrive shipping services from the PostNl
            @param:
            @return: list of dictionaries with shipping service
            @author: Nimesh Jadav  on dated 16-Jan-2019
        """
        shipping_services_obj = self.env['shipping.services.ept']
        services_name = {'3085': '3085-Standard shipment/ Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3385': '3385-Deliver to stated address only/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3090': '3090-Delivery to neighbour + Return when not home/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3390':'3390-Deliver to stated address only + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3086': '3086-COD',             
                         '3091':'3091-COD + Extra cover', 
                         '3093':'3093-COD + Return when not home',
                         '3097':'3097-COD + Extra cover + Return when not home', 
                         '3087':'3087-Extra Cover/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3094':'3087-Extra cover + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery', 
                         '3089':'3089-Signature on delivery + Deliver to stated address only/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3096':'3096-Signature on delivery + Deliver to stated address only + Return when not home/Evening delivery/Sunday delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3189':'3189-Signature on delivery/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3389':'3389-Signature on delivery + Return when not home/Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3533':'3533-Pick up at PostNL location + Signature on Delivery',
                         '3534':'3534-Pick up at  PostNL location + Extra Cover',
                         '3535':'3535-Pick up at  PostNL location + COD',
                         '3536':'3536-Pick up at  PostNL location + COD + Extra Cover',
                         '3543':'3543-Early morning Pick up Points/Pick up at  PostNL location + Signature on Delivery + Notification',
                         '3544':'3544-Early morning Pick up Points/Pick up at  PostNL location + Extra Cover + Notification',
                         '3545':'3545-Early morning Pick up Points/Pick up at  PostNL location + COD + Notification',
                         '3546':'3546-Early morning Pick up Points/Pick up at  PostNL location + COD + Extra Cover + Notification',
                         '2928':'2928-Letterbox suit Extra NL Pickup address ',
                         '3437':'3437-Delivery to neighbour + Age Check',
                         '3438':'3438-Standard shipment + Age Check',
                         '3443':'3443-Extra Cover + Age Check',
                         '3446':'3446-Extra Cover + Retun when not home + Age Check',
                         '3449':'3449-Retun when not home + Age Check',    
                         '3440':'3440-Standard shipment +  ID validation  based on date of birth ',
                         '3444':'3444-Extra Cover +  ID validation  based on date of birth ',
                         '3447':'3447-Extra Cover + Retun when not home + ID validation  based on date of birth ',
                         '3450':'3450-Retun when not home +  ID validation  based on date of birth ',
                         '3442':'3442-Standard shipment +  ID validation  based on ID number ',
                         '3445':'3445-Extra Cover +  ID validation  based on ID number ',
                         '3448':'3448-Extra Cover + Retun when not home + ID validation based on ID number ',
                         '3451':'3451-Retun when not home +  ID validation  based on ID number ',
                         '3571':'3571-Pick up at PostNL location + Age Check',
                         '3572':'3572-Retrieve at PostNL location + ID validation  based on date of birth ',
                         '3573':'3573-Retrieve at PostNL location + ID validation  based on ID number ',
                         '3574':'3574-Pick up at PostNL location + Age Check + Notification',
                         '3575':'3575-Retrieve at PostNL location + ID validation  based on date of birth  + Notification',
                         '3576':'3576-Retrieve at PostNL location + ID validation  based on ID number  + Notfication',
                         '3581':'3581-Pick up at PostNL location + Extra Cover + Age Check',
                         '3582':'3582-Retrieve at PostNL location + Extra Cover + ID validation  based on date of birth ',
                         '3583':'3583-Retrieve at PostNL location + Extra Cover + ID validation  based on ID number ',
                         '3584':'3584-Pick up at PostNL location + Extra Cover + Age Check + Notification',
                         '3585':'3585-Retrieve at PostNL location + Extra Cover + ID validation  based on date of birth  + Notification',
                         '3586':'3586-Retrieve at PostNL location + Extra Cover + ID validation  based on ID number  + Notification',
                         '1010':'1010-Registered letter',
                         '1011':'1011-Registered letter',
                         '1020':'1020-Registered parcels Losse Post',
                         '1410':'1410-Registered letters Partijen Post',
                         '1420':'1420-Registered parcels Partijen Post',
                         '1175':'1175-Letter + ID check',
                         '1178':'1178-Letter + ID validation  based on date of birth ',
                         '1179':'1179-Letter + age check',
                         '1180':'1180-Letter + ID validation  based on ID number ',
                         '3083':'3083-Food  dry and groceries /Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '3084':'3084-Food  cool products / Evening delivery/Sameday delivery/Guaranteed/ Morning delivery',
                         '2285':'2285-Single label variant/Business reply number',
                        #belgium
                         '4960':'4960-Belgium Deliver to stated address only',
                         '4961':'4961-Belgium Delivery to neighbour',
                         '4962':'4962-Belgium Signature on delivery + Deliver to stated address only ',
                         '4963':'4963-Belgium Signature on delivery',
                         '4964':'4964-Belgium COD + Return when not home',
                         '4965':'4965-Belgium Extra cover  EUR 500  +  Deliver to stated address only',
                         '4966':'4966-Belgium COD + Extra cover  EUR 500  + Return when not home',
                         '4924':'4924-België Cash on Delivery',
                        #Destination EU
                         '4940':'4940-EU Pack Special to business',
                         '4950':'4950-EU Pack Special to business  Combilabel  ',
                         '4944':'4944-EU Pack Special to consumer',
                         '4952':'4952-EU Pack Special to consumer  Combilabel ',                      
                         '3606':'3606-AVG Pallet Pharma&Care 2-8 C /Guaranteed delivery Cargo/Cargo Pickup',
                         '3607':'3607-AVG Pallet Pharma&Care 15-25 C /Guaranteed delivery Cargo/ Cargo Pickup',
                         '3608':'3608-AVG Cargo Parcel Pharma&Care 2-8 C /Guaranteed delivery Cargo /Cargo Pickup',
                         '3609':'3609-AVG Cargo Parcel Pharma&Care 15-25 C /Guaranteed delivery Cargo/ Cargo Pickup',
                         '3610':'3610-AVG Pallet NL /Guaranteed delivery Cargo /Cargo Pickup',
                         '3611':'3611-AVG Pallet NL + COD / Guaranteed delivery Cargo',
                         '3630':'3630-AVG Parcel Plus NL / Guaranteed delivery Cargo/ Cargo Pickup',
                         '3631':'3631-AVG Parcel Plus NL + COD / Guaranteed delivery Cargo',
                         '3657':'3657-AVG Half Europallet NL / Guaranteed delivery Cargo /Cargo Pickup',
                         '3677':'3677- AVG Half Europallet NL +COD / Guaranteed delivery Cargo',
                         '3696':'3696-AVG Roll Cage container NL / Guaranteed delivery Cargo /Cargo Pickup',
                         '3618':'3618-AVG Pallet BE /Cargo Pickup',
                         '3619':'3619-AVG Pallet BE + COD',
                         '3638':'3638-AVG Parcel Plus BE /Cargo Pickup',
                         '3639':'3639-AVG Parcel Plus BE + COD',
                         '3658':'3658-AVG Half Europallet BE /Cargo Pickup',
                         '3678':'3678-AVG Half Europallet BE +COD',
                         '3697':'3697-AVG Roll Cage container BE /Cargo Pickup',
                         '3622':'3622-AVG Pallet LU/ Cargo Pickup',
                         '3623':'3623-AVG Pallet LU + COD',
                         '3642':'3642-AVG Parcel Plus LU /Cargo Pickup',
                         '3643':'3643-AVG Parcel Plus LU + COD',
                         '3659':'3659-AVG Half Europallet LU /Cargo Pickup',
                         '3679':'3679-AVG Half Europallet LU +COD',
                         '3626':'3626-AVG Euro Freight Pallet',
                         '3627':'3627-AVG Euro Freight Parcel Plus',
                         '3628':'3628-Extra@Home Top service 2 person delivery NL Available destinations-NL ',
                         '3629':'3629-Extra@Home Top service Btl 2 person delivery  Available destinations-BE;LU ',
                         '3653':'3653-Extra@Home Top service 1 person delivery NL  Available destinations-NL ' ,
                         '3783':'3783-Extra@Home Top service Btl 1 person delivery  Available destinations-BE;LU ',
                         '3790':'3790-Extra@Home Drempelservice 1 person delivery NL  Available destinations-NL ',
                         '3791':'3791-Extra@Home Drempelservice 2 person delivery NL',
                         '3792':'3792-Extra@Home Drempelservice Btl 1 person delivery  Available destinations-BE;LU ',
                         '3793':'3793-Extra@Home Drempelservice Btl 2 persons delivery  Available destinations-BE;LU '} 
        services = shipping_services_obj.search([('shipping_instance_id', '=', self.id)])
        services.unlink()
        for company in self.company_ids:
            for service in services_name:
                vals = {'shipping_instance_id': self.id, 'service_code': service,'service_name': services_name.get(service, False), 'company_ids': [(4, company.id)]}
                shipping_services_obj.create(vals)

    @api.model
    def postnl_ept_quick_add_shipping_services(self, service_type, service_name):
        """ Allow you to get the default shipping services value while creating quick
            record from the Shipping Service for postnl
            @param service_type: Service type of postnl
            @return: dict of default value set
            @author: Jigar Vagadiya on dated 11-Feb-2019
        """
        return {'default_postnl_product': service_type,
                'default_name': service_name}

