# -*- coding: utf-8 -*-
# #############################################################################
#
#    Copyright Mollie (C) 2019
#    Contributor: Eezee-It <info@eezee-it.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import logging

from mollie.api.client import Client
import werkzeug

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

PAYLATER_METHODS = ['klarnapaylater']

_logger = logging.getLogger(__name__)


class WebsiteSaleMollie(WebsiteSale):

    @http.route(['/shop/cart/update_payment_method_json'], type='json',
                auth="public", methods=['POST'], website=True, csrf=False)
    def update_payment_method_json(self, method_id):
        order = request.website.sale_get_order()
        if order and method_id != 0:
            order.acquirer_method = method_id or False
        elif order and method_id == 0:
            order.acquirer_method = False
        return True

    @http.route()
    def payment(self, **post):
        """ filter payment methods by location and currency
        """
        response = super(WebsiteSaleMollie, self).payment(**post)
        if response.qcontext.get('website_sale_order', False):
            response.qcontext['website_sale_order'].acquirer_method = False
        return response


class MollieController(http.Controller):
    _notify_url = '/payment/mollie/notify'
    _redirect_url = '/payment/mollie/redirect'
    _cancel_url = '/payment/mollie/cancel'
    _mollie_client = Client()

    @http.route([
        '/payment/mollie/notify'],
        type='http', auth='none', methods=['GET'])
    def mollie_notify(self, **post):
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect('/payment/process')

    @http.route([
        '/payment/mollie/redirect'], type='http', auth="none", methods=['GET'])
    def mollie_redirect(self, **post):
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect('/payment/process')

    @http.route([
        '/payment/mollie/cancel'], type='http', auth="none", methods=['GET'])
    def mollie_cancel(self, **post):
        request.env['payment.transaction'].sudo().form_feedback(post, 'mollie')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/payment/mollie/intermediate'], type='http',
                auth="none", methods=['POST'], csrf=False)
    def mollie_intermediate(self, **post):
        base_url = post['BaseUrl']
        tx_reference = post['Description']
        currency = post['Currency']
        amount = post['Amount']
        order_model = request.env['sale.order'].sudo()
        OrderId = post.get('OrderId', '')
        OrderId = int(OrderId)
        order = order_model.browse(OrderId)
        method = order.acquirer_method and\
            order.acquirer_method.acquirer_reference
        payment_tx = request.env['payment.transaction'].sudo(
        )._mollie_form_get_tx_from_data({'reference': tx_reference})
        webhookUrl = '%s/web#id=%s&action=%s&model=%s&view_type=form' % (
            base_url, payment_tx.id,
            'payment.action_payment_transaction', 'payment.transaction')
        payload = {
            'amount': {
                'currency': currency,
                'value': amount
            },
            'description': tx_reference,
            'redirectUrl': "%s%s?reference=%s" % (base_url,
                                                  self._redirect_url,
                                                  tx_reference),
            'metadata': {
                'OrderId': str(OrderId),
                'OdooTransactionRef': tx_reference,
                'webhookUrl': webhookUrl,
                "customer": {
                    "locale": post.get('Language', 'nl_NL'),
                    "last_name": post.get('Name', ''),
                    "address": post.get('Address', ''),
                    "zip_code": post.get('Zip', ''),
                    "city": post.get('Town', ''),
                    "country": post.get('Country', ''),
                    "phone": post.get('Phone', ''),
                    "email": post.get('Email', '')
                }
            },
            "locale": post.get('Language', 'nl_NL'),
        }
        if method:
            payload.update({'method': method, })

        self._mollie_client.set_api_key(post['Key'])
        order_response = order.mollie_order_sync(tx_reference)
        if order_response and order_response["status"] == "created":
            if '_embedded' in order_response:
                embedded = order_response['_embedded']
                if 'payments' in embedded:
                    payment = embedded['payments'][-1]
                    payment_tx.write({"acquirer_reference": payment["id"]})

            checkout_url = order_response["_links"]["checkout"]["href"]
            return werkzeug.utils.redirect(checkout_url)
        return werkzeug.utils.redirect("/")
