import time
import requests
import hmac
import hashlib
import base64
from datetime import datetime
import collections
from enum import Enum

from xml.etree import ElementTree

from .models import Orders, Payments, Shipments, ProcessStatus

# custom Method Models For DreamBits
from .models import PurchasableShippingLabels, ReturnItems, DeliveryWindow
from .models import OffersResponse, OfferFile  # DeleteBulkRequest
from .models import FbbTransports, InventoryResponse, Inbound
from .models import Errors

__all__ = ['PlazaAPI']


class TransporterCode(Enum):
    """
    https://developers.bol.com/documentatie/plaza-api/developer-guide-plaza-api/appendix-a-transporters/
    """
    DHLFORYOU = 'DHLFORYOU'
    UPS = 'UPS'
    KIALA_BE = 'KIALA-BE'
    KIALA_NL = 'KIALA-NL'
    TNT = 'TNT'
    TNT_EXTRA = 'TNT-EXTRA'
    TNT_BRIEF = 'TNT_BRIEF'
    TNT_EXPRESS = 'TNT-EXPRESS'
    SLV = 'SLV'
    DYL = 'DYL'
    DPD_NL = 'DPD-NL'
    DPD_BE = 'DPD-BE'
    BPOST_BE = 'BPOST_BE'
    BPOST_BRIEF = 'BPOST_BRIEF'
    BRIEFPOST = 'BRIEFPOST'
    GLS = 'GLS'
    FEDEX_NL = 'FEDEX_NL'
    FEDEX_BE = 'FEDEX_BE'
    OTHER = 'OTHER'
    DHL = 'DHL'
    DHL_DE = 'DHL_DE'
    DHL_GLOBAL_MAIL = 'DHL-GLOBAL-MAIL'
    TSN = 'TSN'
    FIEGE = 'FIEGE'
    TRANSMISSION = 'TRANSMISSION'
    PARCEL_NL = 'PARCEL-NL'
    LOGOIX = 'LOGOIX'
    PACKS = 'PACKS'

    @classmethod
    def to_string(cls, transporter_code):
        if isinstance(transporter_code, TransporterCode):
            transporter_code = transporter_code.value
        assert transporter_code in map(
            lambda c: c.value, list(TransporterCode))
        return transporter_code


class MethodGroup(object):

    def __init__(self, api, group):
        self.api = api
        self.group = group

    def request(self, method, path='', params={}, data=None,
                accept="application/xml"):
        uri = '{prefix}/{group}/{version}{path}'.format(
            prefix='/services/rest' if self.group!='offers' else '',
            group=self.group,
            version=self.api.version,
            path=path)
        xml = self.api.request(method, uri, params=params, data=data,
                               accept=accept)
        return xml

    def create_request_xml(self, root, **kwargs):
        elements = self._create_request_xml_elements(1, **kwargs)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<{root} xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
{elements}
</{root}>
""".format(root=root, elements=elements)
        return xml

    def create_request_offers_xml(self, root, **kwargs):
        elements=''
        for kwarg in kwargs.get('RetailerOffer'):
            element="<RetailerOffer>"
            element+="<EAN>%s</EAN>"%(kwarg.Meta.EAN)
            element+="<Condition>%s</Condition>"%(kwarg.Meta.Condition)
            element+="<Price>%s</Price>"%(kwarg.Meta.Price)
            element+="<DeliveryCode>%s</DeliveryCode>"%(kwarg.Meta.DeliveryCode)
            element+="<QuantityInStock>%s</QuantityInStock>"%(kwarg.Meta.QuantityInStock)
            element+="<Publish>%s</Publish>"%(str(kwarg.Meta.Publish).lower())
            element+="<ReferenceCode>%s</ReferenceCode>"%(kwarg.Meta.ReferenceCode and kwarg.Meta.ReferenceCode or '')
            element+="<Description>%s</Description>"%(kwarg.Meta.Description and kwarg.Meta.Description or '')
            element+="<Title>%s</Title>"%(kwarg.Meta.Title)
            element+="<FulfillmentMethod>%s</FulfillmentMethod>"%(kwarg.Meta.FulfillmentMethod)
            element+="</RetailerOffer>"
            elements+=element
            
        xml = """<?xml version="1.0" encoding="UTF-8"?><{root} xmlns="https://plazaapi.bol.com/offers/xsd/api-2.0.xsd">{elements}</{root}>""".format(root=root, elements=elements)
        return xml

    def _create_request_xml_elements(self, indent, **kwargs):
        # sort to make output deterministic
        kwargs = collections.OrderedDict(sorted(kwargs.items()))
        xml = ''
        for tag, value in kwargs.items():
            if value is not None:
                prefix = ' ' * 4 * indent
                if not isinstance(value, list):
                    if isinstance(value, dict):
                        text = '\n{}\n{}'.format(
                            self._create_request_xml_elements(
                                indent + 1, **value),
                            prefix)
                    elif isinstance(value, datetime):
                        text = value.isoformat()
                    else:
                        text = str(value)
                    # TODO: Escape! For now this will do I am only dealing
                    # with track & trace codes and simplistic IDs...
                    if xml:
                        xml += '\n'
                    xml += prefix
                    xml += "<{tag}>{text}</{tag}>".format(
                        tag=tag,
                        text=text
                    )
                else:
                    for item in value:
                        if isinstance(item, dict):
                            text = '\n{}\n{}'.format(
                                self._create_request_xml_elements(
                                    indent + 1, **item),
                                prefix)
                        else:
                            text = str(item)
                        # TODO: Escape! For now this will do I am only dealing
                        # with track & trace codes and simplistic IDs...
                        if xml:
                            xml += '\n'
                        xml += prefix
                        xml += "<{tag}>{text}</{tag}>".format(
                            tag=tag,
                            text=text
                        )
        return xml


class OrderMethods(MethodGroup):

    def __init__(self, api):
        super(OrderMethods, self).__init__(api, 'orders')
      
    def list(self, method="GET", path='', params={}, data=None,
                accept="application/vnd.orders-v2.1+xml"):
        uri = '{prefix}/{group}/{version}{path}'.format(
            prefix='/services/rest',
            group=self.group,
            version=self.api.version,
            path=path)
        xml = self.api.request(method, uri, params=params, data=data,
                               accept=accept)
        return Orders.parse(self.api, xml)


class PaymentMethods(MethodGroup):

    def __init__(self, api):
        super(PaymentMethods, self).__init__(api, 'payments')

    def list(self, year, month):
        xml = self.request('GET', '/%d%02d' % (year, month))
        return Payments.parse(self.api, xml)


class ProcessStatusMethods(MethodGroup):

    def __init__(self, api):
        super(ProcessStatusMethods, self).__init__(api, 'process-status')

    def get(self, id):
        xml = self.request('GET', '/{}'.format(id))
        return ProcessStatus.parse(self.api, xml)


class ShipmentMethods(MethodGroup):

    def __init__(self, api):
        super(ShipmentMethods, self).__init__(api, 'shipments')

    def list(self,shipment_fullfillment_by = 'fbb', page=None,order_id=False):
        params={}
        if page is not None:
            params.update({'page': page})
        if shipment_fullfillment_by:
            params.update({'fulfilment-method': shipment_fullfillment_by})
        if order_id:
            params.update({'order-id': order_id})
        uri = '{prefix}/{group}/{version}'.format(
            prefix='/services/rest' if self.group!='offers' else '',
            group=self.group,
            version=self.api.version)
        xml = self.api.request('GET',uri, params=params,accept="application/vnd.shipments-v2.1+xml")
        return Shipments.parse(self.api, xml)

    def create(self, order_item_id,
               shipment_reference=None, transporter_code=None,
               track_and_trace=None, shipping_label_code=None):
        # Moved the params to a dict so it can be easy to add/remove parameters
        values = {
            'OrderItemId': order_item_id,
            #'ShipmentReference': shipment_reference,
        }

        if transporter_code:
            transporter_code = TransporterCode.to_string(
                transporter_code)

        if shipping_label_code:
            values['ShippingLabelCode'] = shipping_label_code
        elif transporter_code and track_and_trace:
            values['Transport'] = {
                'TransporterCode': transporter_code,
                'TrackAndTrace': track_and_trace
            }
        elements = self._create_request_xml_elements(1, **values)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<{root} xmlns="https://plazaapi.bol.com/services/xsd/v2.1/plazaapi.xsd">
{elements}
</{root}>
""".format(root='ShipmentRequest', elements=elements)

        response = self.request('POST', data=xml,accept="application/vnd.shipments-v2.1+xml")
        return ProcessStatus.parse(self.api, response)


class TransportMethods(MethodGroup):

    def __init__(self, api):
        super(TransportMethods, self).__init__(api, 'transports')

    def update(self, id, transporter_code, track_and_trace):
        transporter_code = TransporterCode.to_string(transporter_code)
        xml = self.create_request_xml(
            'ChangeTransportRequest',
            TransporterCode=transporter_code,
            TrackAndTrace=track_and_trace)
        response = self.request('PUT', '/{}'.format(id), data=xml)
        return ProcessStatus.parse(self.api, response)

    def getSingle(self, transportId, shippingLabelId, file_location):
        content = self.request('GET', '/{}/shipping-label/{}'.format(
            transportId,
            shippingLabelId),
            params={}, data=None, accept="application/pdf")
        # Now lets store this content in pdf:

        with open(file_location, 'wb') as f:
                f.write(content)


class PurchasableShippingLabelsMethods(MethodGroup):

    def __init__(self, api):
        super(PurchasableShippingLabelsMethods, self).__init__(
            api,
            'purchasable-shipping-labels')

    def get(self, id):
        params = {'orderItemId': id}
        xml = self.request('GET', params=params)
        return PurchasableShippingLabels.parse(self.api, xml)


class ReturnItemsMethods(MethodGroup):

    def __init__(self, api):
        super(ReturnItemsMethods, self).__init__(api, 'return-items')

    def getUnhandled(self):
        xml = self.request('GET', path="/unhandled", accept="application/xml")
        return ReturnItems.parse(self.api, xml)

    def getHandle(self, orderId, status_reason, qty_return):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<ReturnItemStatusUpdate xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
    <StatusReason>{reason}</StatusReason>
    <QuantityReturned>{qty}</QuantityReturned>
</ReturnItemStatusUpdate>
""".format(reason=status_reason,qty=qty_return)
        uri="/services/rest/return-items/v2/%s/handle"%(orderId)
        response = self.api.request("PUT",uri=uri, data=xml,accept="application/xml")
        return ProcessStatus.parse(self.api, response)

class OffersMethods(MethodGroup):

    def __init__(self, api):
        super(OffersMethods, self).__init__(api, 'offers')

    def upsertOffers(self, offers=None, path='/', params={},
                     data=None, accept="application/xml"):
        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path=path)
        response = self.api.request('PUT', uri, params=params,
                                    data=data, accept=accept)
        return response

    def getSingleOffer(self, ean, path='/', params={},
                       data=None, accept="application/xml"):

        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/{}'.format(ean))
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return OffersResponse.parse(self.api, response)

    def getOffersFileName(self, path='/', params={},
                          data=None, accept="application/xml"):

        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/export/')
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return OfferFile.parse(self.api, response)

    def getOffersFile(self, csv, path='/', params={},
                      data=None, accept="text/csv"):
        csv_path = csv.split("/v2/")
        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/{}'.format(csv_path[1]))
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return response

    def deleteOffers(self, offers=None, path='/', params={},
                     data=None, accept="application/xml"):
        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path=path)
        response = self.api.request('DELETE', uri, params=params,
                                    data=data, accept=accept)
        if response is True:
            return response

class InboundMethods(MethodGroup):
    
    def __init__(self, api):
        super(InboundMethods, self).__init__(api, 'inbounds')
    
    def getDeliveryWindow(self,delivery_date,qty_to_send):
        params={'delivery-date':delivery_date,'items-to-send':qty_to_send}
        uri = "/services/rest/inbounds/delivery-windows"
        response = self.api.request('GET', uri,params=params)
        return DeliveryWindow.parse(self.api,response)
    
    def create_shipment(self,shipment_data):
        uri = "/services/rest/inbounds"
        response = self.api.request('POST',uri,data=shipment_data)
        return ProcessStatus.parse(self.api,response)
    
    def getProductLabel(self,product_data,format):
        uri = "/services/rest/inbounds/productlabels"
        params={'format':format}
        response = self.api.request('POST',uri,data=product_data,params=params,accept="application/pdf")
        return response
    
    def getShipmentLabel(self,inbound_id):
        uri = "/services/rest/inbounds/%s/shippinglabel"%(inbound_id)
        response = self.api.request('GET',uri,accept="application/pdf")
        return response
    
    def getPackagingList(self,inbound_id):
        uri = "/services/rest/inbounds/%s/packinglistdetails"%(inbound_id)
        response = self.api.request('GET',uri,accept="application/pdf")
        return response
    
    def getInboundShipmentList(self,page=None):
        uri = "/services/rest/inbounds"
        if page is not None:
            params={'page':page}
        response = self.api.request('GET',uri,params=params)
        return response
    
    def getInboundShipment(self,shipment_id):
        uri = "/services/rest/inbounds/%s"%(shipment_id)
        response = self.api.request('GET',uri)
        return Inbound.parse(self.api, response)

class FbbTransportsMethods(MethodGroup):
    
    def __init__(self, api):
        super(FbbTransportsMethods, self).__init__(api, 'fbbtransports')
        
    def getFbbTransports(self):
        uri = "/services/rest/inbounds/fbb-transporters/"
        response = self.api.request('GET', uri)
        return FbbTransports.parse(self.api, response)
    
class InventoryMethods(MethodGroup):
    
    def __init__(self, api):
        super(InventoryMethods, self).__init__(api, 'fbb_inventory')
        
    def getInventory(self,page=None):
        uri = "/services/rest/inventory"
        if page is not None:
            params={'page':page} 
        response = self.api.request('GET', uri,params=params)
        return InventoryResponse.parse(self.api, response)

class PlazaAPI(object):

    def __init__(self, public_key, private_key, test=False, timeout=None,
                 session=None):

        self.public_key = public_key
        self.private_key = private_key
        self.url = 'https://%splazaapi.bol.com' % ('test-' if test else '')

        self.version = 'v2'
        self.timeout = timeout
        self.orders = OrderMethods(self)
        self.payments = PaymentMethods(self)
        self.shipments = ShipmentMethods(self)
        self.process_status = ProcessStatusMethods(self)
        self.transports = TransportMethods(self)
        self.labels = PurchasableShippingLabelsMethods(self)
        self.session = requests.Session()
        self.return_items = ReturnItemsMethods(self)
        self.offers = OffersMethods(self)
        self.inbounds = InboundMethods(self)
        self.fbbtransports = FbbTransportsMethods(self)
        self.fbb_inventory = InventoryMethods(self)

    def request(self, method, uri, params={},
                data=None, accept="application/xml"):
        content_type = 'application/xml%s'%('; charset=UTF-8' if not accept.__contains__("application/vnd") else '')
        date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
        msg = """{method}

{content_type}
{date}
x-bol-date:{date}
{uri}""".format(content_type=content_type,
                date=date,
                method=method,
                uri=uri)
        h = hmac.new(
            self.private_key.encode('utf-8'),
            msg.encode('utf-8'), hashlib.sha256)
        b64 = base64.b64encode(h.digest())

        signature = self.public_key.encode('utf-8') + b':' + b64

        headers = {'Content-Type': content_type,
                   'X-BOL-Date': date,
                   'X-BOL-Authorization': signature.decode('utf-8'),
                   'accept': accept}

        request_kwargs = {
            'method': method,
            'url': self.url + uri,
            'params': params,
            'headers': headers,
            'timeout': self.timeout,
        }
        if data:
            request_kwargs['data'] = data

        resp = self.session.request(**request_kwargs)

        if request_kwargs['url'] == 'https://plazaapi.bol.com/offers/v2/':
            if resp.status_code == 202 and resp.text is not None:
                return True
            else:
                return  Errors.parse(self, ElementTree.fromstring(resp.content))
                #tree = ElementTree.fromstring(resp.text)
                #return tree

        if 'https://plazaapi.bol.com/offers/v2/export/' in request_kwargs['url']:
            if accept == "text/csv":
                return resp.text
        if 'https://plazaapi.bol.com/services/rest/inbounds' == request_kwargs['url']:
            if request_kwargs['method']=='GET':
                return resp.content
            else:
                tree = ElementTree.fromstring(resp.content)
                return tree
        
        resp.raise_for_status()

        if accept == "application/pdf":
            return resp.content
        elif accept == "text/csv":
            return resp.text
        else:
            tree = ElementTree.fromstring(resp.content)
            return tree
