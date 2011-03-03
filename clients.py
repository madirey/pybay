from base64 import b64encode
from xml.dom.minidom import parseString
import hashlib, logging

# Author: Matt Caldwell
# Date: December 2010

class PyBayClient(object):
	""" A set of clients for easy interoperability with eBay's public APIs.
	
	"""
	def __init__(self, config=None, sandbox=False):
		"""
		
		"""
		self.auth_token = None
		self.sandbox = sandbox
		self.test_backend = { }
		
		if config:
			self._dev_id = config.get('dev_id', None)
			self._app_id = config.get('app_id', None)
			self._cert_id = config.get('cert_id', None)
			self._site_id = config.get('site_id', '0') # default US
	
	def _get_headers(self, call_type, content_type='text/xml'):
		raise NotImplementedError
	
	def _build_xml_body(self, call_type, xml_data=None):
		raise  NotImplementedError
	
	def _send_request(self, call_type, xml_data=None):
		"""
		
		"""
		import httplib2

		headers = self._get_headers(call_type)
		body = self._build_xml_body(call_type, xml_data)

		http = httplib2.Http()
		return http.request(self._url, 'POST', headers=headers, body=body)
	
	def set_config(self, config):
		self._dev_id = config.get('dev_id', None)
		self._app_id = config.get('app_id', None)
		self._cert_id = config.get('cert_id', None)
		self._site_id = config.get('site_id', '0') # default US

class TradingApiClient(PyBayClient):
	def __init__(self, config=None, sandbox=False):
		"""
		
		"""
		super(TradingApiClient, self).__init__(config, sandbox)

		self._version = '699'
		self._url = 'https://api%s.ebay.com/ws/api.dll' % ('.sandbox' if self.sandbox else '')
		self.session_id = None

		if config:
			self._ru_name = config.get('ru_name', None)
	
	def _get_headers(self, call_type, content_type='text/xml'):
		"""
		
		"""
		headers =	{	'X-EBAY-API-COMPATIBILITY-LEVEL': self._version,
						'X-EBAY-API-DEV-NAME': self._dev_id,
						'X-EBAY-API-APP-NAME': self._app_id,
						'X-EBAY-API-CERT-NAME': self._cert_id,
						'X-EBAY-API-SITEID': self._site_id,
						'X-EBAY-API-CALL-NAME': call_type,
						'Content-Type': content_type
		}
		
		return headers
	
	def _build_xml_body(self, call_type, xml_data=None):
		"""
		
		"""
		body = 	'<?xml version="1.0" encoding="utf-8"?>'
		body +=	'<%sRequest xmlns="urn:ebay:apis:eBLBaseComponents">' % call_type
		if self.auth_token:
			body += '<RequesterCredentials>'
			body += '<eBayAuthToken>%s</eBayAuthToken>' % self.auth_token
			body += '</RequesterCredentials>'
		body += xml_data if xml_data is not None else ''
		body += '</%sRequest>' % call_type
		
		return body
	
	def set_config(self, config):
		"""
		
		"""
		super(TradingApiClient, self).set_config(config)
		self._ru_name = config.get('ru_name')
	
	def get_session_id(self):
		"""
		
		"""
		logging.debug('getting session id')
		logging.debug('ru name: %s' % self._ru_name)
		session_id = None
		xml_data = '<RuName>%s</RuName>' % self._ru_name
		response, content = self._send_request('GetSessionID', xml_data)
		logging.debug('response=%s' % response)
		logging.debug('content=%s' % content)
		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data
		
		if ack == 'Success':
			session_id = dom.getElementsByTagName('SessionID')[0].childNodes[0].data
		else:
			pass # TODO: Exception here?
		
		self.session_id = session_id
		return session_id
	
	def get_auth_token(self, session_id=None):
		"""
		
		"""
		if not session_id:
			session_id = self.session_id

		logging.debug('session id: %s' % session_id)

		auth_token = None
		auth_token_expire_time = None
		xml_data = '<SessionID>%s</SessionID>' % session_id
		response, content = self._send_request('FetchToken', xml_data)
		
		logging.debug('content: %s' % content)

		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data
		
		if ack == 'Success':
			logging.debug('success')

			auth_token = dom.getElementsByTagName('eBayAuthToken')[0].childNodes[0].data
			auth_token_expire_time = dom.getElementsByTagName('HardExpirationTime')[0].childNodes[0].data
		else:
			logging.debug('failure') # TODO: Exception here?
		
		self.auth_token = auth_token
		self.auth_token_expire_time = auth_token_expire_time
		return auth_token
	
	def revoke_token(self, auth_token=None):
		if auth_token:
			self.auth_token = auth_token
		
		xml_data = '<UnsubscribeNotification>True</UnsubscribeNotification>'
		response, content = self._send_request('RevokeToken', xml_data)
		
		logging.debug('content: %s' % content)
		
		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data
		
		if ack == 'Success':
			logging.debug('success')
			return True
		
		else:
			logging.debug('failure') # TODO: Exception here?
			return False
	
	def confirm_identity(self, session_id=None):
		"""
		"""
		if not session_id:
			session_id = self.session_id
		
		logging.debug('session id: %s' % session_id)
		
		xml_data = '<SessionID>%s</SessionID>' % session_id
		response, content = self._send_request('ConfirmIdentity', xml_data)
		
		logging.debug('content: %s' % content)
		
		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data
		
		if ack == 'Success':
			logging.debug('success')
			
			user_id = dom.getElementsByTagName('UserID')[0].childNodes[0].data
		else:
			logging.debug('failure') # TODO: Exception here?
		
		self.user_id = user_id
		return user_id
	
	def get_redirect_url(self):
		"""
		
		"""
		import urllib
		self.get_session_id()
		logging.debug('ru_name=%s' % self._ru_name)
		logging.debug('session_id=%s' % self.session_id)
		return 'https://signin%s.ebay.com/ws/eBayISAPI.dll?SignIn&RuName=%s&SessID=%s' %\
			('.sandbox' if self.sandbox else '', urllib.quote(self._ru_name), urllib.quote(self.session_id))

	def set_notification_preferences(self, prefs):
		""" Uses the eBay Trading API to set a user's notification preferences.
		
		Transforms a dictionary of preferences, prefs, into an XML request compliant with eBay's
		Trading API, sends the request to eBay and processes the response.
		
		The 'prefs' dictionary should be in a format as indicated in the doctest(s) below.

		>>> prefs = { }
		>>> prefs['ApplicationDeliveryPreferences.AlertEmail'] = 'mailto://magicalbookseller@yahoo.com'
		>>> prefs['ApplicationDeliveryPreferences.AlertEnable'] = 'Enable'
		>>> prefs['ApplicationDeliveryPreferences.ApplicationEnable'] = 'Enable'
		>>> prefs['ApplicationDeliveryPreferences.ApplicationURL'] = 'http://magicalbookseller.com'
		>>> prefs['ApplicationDeliveryPreferences.DeviceType'] = 'Platform'
		>>> prefs['UserDeliveryPreferenceArray.NotificationEnable.MyMessageseBayMessageHeader'] = 'Enable'
		>>> prefs['UserDeliveryPreferenceArray.NotificationEnable.Feedback'] = 'Enable'
		>>> prefs['UserDeliveryPreferenceArray.NotificationEnable.EndOfAuction'] = 'Enable'
		>>> prefs['DeliveryURLName'] = 'http://magicalbookseller.com/api/subscriptions/ebay'
		>>> client = TradingApiClient()
		>>> client.test_backend = { }
		>>> client.set_notification_preferences(prefs)
		>>> client.test_backend.get('xml_data')
		... # doctest: +NORMALIZE_WHITESPACE
		'<ApplicationDeliveryPreferences>
		  <ApplicationEnable>Enable</ApplicationEnable>
		  <ApplicationURL>http://magicalbookseller.com</ApplicationURL>
		  <AlertEnable>Enable</AlertEnable>
		  <AlertEmail>mailto://magicalbookseller@yahoo.com</AlertEmail>
		  <DeviceType>Platform</DeviceType>
		</ApplicationDeliveryPreferences>
		<DeliveryURLName>http://magicalbookseller.com/api/subscriptions/ebay</DeliveryURLName>
		<UserDeliveryPreferenceArray>
		  <NotificationEnable>
		    <EventType>Feedback</EventType>
		    <EventEnable>Enable</EventEnable>
		  </NotificationEnable>
		  <NotificationEnable>
		    <EventType>MyMessageseBayMessageHeader</EventType>
		    <EventEnable>Enable</EventEnable>
		  </NotificationEnable>
		  <NotificationEnable>
		    <EventType>EndOfAuction</EventType>
		    <EventEnable>Enable</EventEnable>
		  </NotificationEnable>
		</UserDeliveryPreferenceArray>'
		>>>
		"""
		app_delivery_prefs = dict((k, prefs[k]) for k in prefs.keys() if k.split('.')[0] ==
			'ApplicationDeliveryPreferences')
		event_property_prefs = dict((k, prefs[k]) for k in prefs.keys() if k.split('.')[0] == 'EventProperty')
		user_data_prefs = dict((k, prefs[k]) for k in prefs.keys() if k.split('.')[0] == 'UserData')
		user_delivery_prefs = dict((k, prefs[k]) for k in prefs.keys() if k.split('.')[0] ==
			'UserDeliveryPreferenceArray')

		xml_data = ''
		if app_delivery_prefs:
			xml_data +=	'<ApplicationDeliveryPreferences>'
			for k, v in app_delivery_prefs.items():
				xml_data += '<%s>%s</%s>' % (k.split('.')[1], v, k.split('.')[1])
			xml_data +=	'</ApplicationDeliveryPreferences>'
		
		if prefs.get('DeliveryURLName'):
			xml_data +=	'<DeliveryURLName>%s</DeliveryURLName>' % prefs['DeliveryURLName']
		
		if event_property_prefs:
			xml_data +=	'<EventProperty>'
			for k, v in event_property_prefs.items():
				xml_data += '<%s>%s</%s>' % (k.split('.')[1], v, k.split('.')[1])
			xml_data += '</EventProperty>'
		
		if user_data_prefs:
			xml_data +=	'<UserData>'
			for k, v in user_data_prefs.items():
				xml_data += '<%s>%s</%s>' % (k.split('.')[1], v, k.split('.')[1])
			xml_data +=	'</UserData>'
		
		if user_delivery_prefs:
			notification_prefs = dict((k, user_delivery_prefs[k]) for k in user_delivery_prefs.keys() if k.split('.')[1] ==
				'NotificationEnable')

			xml_data +=	'<UserDeliveryPreferenceArray>'
			for k, v in notification_prefs.items():
				xml_data += '<NotificationEnable>'
				xml_data += '<EventType>%s</EventType>' % k.split('.')[2]
				xml_data += '<EventEnable>%s</EventEnable>' % v
				xml_data += '</NotificationEnable>'
			xml_data += '</UserDeliveryPreferenceArray>'

		if self.test_backend is not None:
			self.test_backend['xml_data'] = xml_data
		
		response, content = self._send_request('SetNotificationPreferences', xml_data)
		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data

		if ack == 'Success':
			return True
		else: # TODO: exception here?
			return False
	
	def respond_to_feedback(self, feedback_id, response_type, response_text, target_user_id):
		xml_data =	'<FeedbackID>%s</FeedbackID>' % feedback_id
		xml_data +=	'<ResponseType>%s</ResponseType>' % response_type
		xml_data += '<ResponseText>%s</ResponseText>' % response_text
		xml_data +=	'<TargetUserID>%s</TargetUserID>' % target_user_id
		
		response, content = self._send_request('RespondToFeedback', xml_data)
		dom = parseString(content)
		ack = dom.getElementsByTagName('Ack')[0].childNodes[0].data
		
		if ack == 'Success':
			return True
		else: # TODO: exception here?
			return False

class ClientAlertsClient(PyBayClient):
	def __init__(self, config=None, sandbox=False):
		"""
		
		"""
		super(ClientAlertsClient, self).__init__(config, sandbox)
		self._version = '691'
		self._url = 'http://clientalerts.ebay.com/ws/ecasvc/ClientAlerts'

class PlatformNotificationsClient(PyBayClient):
	def __init__(self, config=None, sandbox=False):
		"""
		
		"""
		super(PlatformNotificationsClient, self).__init__(config, sandbox)

		self._version = '699'

		if config:
			self._ru_name = config.get('ru_name', None)
	
	def verify_signature(self, signature, timestamp):
		hash_me = '%s%s%s%s' % (timestamp, self._dev_id, self._app_id, self._cert_id)
		hash = hashlib.md5(hash_me).digest()
		encoded_hash = b64encode(hash)
	
		logging.debug('signature=%s' % signature)
		logging.debug('computed signature=%s' % encoded_hash)
	
		# compare hashes
		if encoded_hash != signature:
			logging.warning('hashes do not match')
			return False
		
		return True

class PlatformNotification(object):
	_SOAP_ACTION_RESPONSES = {
		'BidReceived': 'GetItemResponse',
		'FeedbackReceived': 'GetFeedbackResponse',
		'ItemLost': 'GetItemResponse',
		'ItemSold': 'GetItemResponse',
		'ItemUnsold': 'GetItemResponse',
		'ItemWon': 'GetItemResponse',
		'MyMessagesM2MMessage': 'GetMyMessagesResponse',
		'MyMessagesHighPriorityMessage': 'GetMyMessagesResponse',
		'OutBid': 'GetItemResponse',
		'TokenRevocation': '?',
	}
	
	_SOAP_ACTION_WRAPPERS = {
		'BidReceived': 'Item',
		'FeedbackReceived': 'FeedbackDetailArray.FeedbackDetail',
		'ItemLost': 'Item',
		'ItemSold': 'Item',
		'ItemUnsold': 'Item',
		'ItemWon': 'Item',
		'MyMessagesM2MMessage': 'Messages.Message',
		'MyMessagesHighPriorityMessage': 'Messages.Message',
		'OutBid': 'Item',
		'TokenRevocation': '?',
	}
	
	_SOAP_ACTION_SENDERS = {
		'BidReceived': 'SellingStatus.HighBidder.UserID',
		'FeedbackReceived': 'CommentingUser',
		'ItemLost': 'SellingStatus.HighBidder.UserID',
		'ItemSold': 'SellingStatus.HighBidder.UserID',
		'ItemUnsold': None,
		'ItemWon': None,
		'MyMessagesM2MMessage': 'Sender',
		'MyMessagesHighPriorityMessage': 'Sender',
		'OutBid': 'SellingStatus.HighBidder.UserID',
		'TokenRevocation': '?',
	}
	
	_SOAP_ACTION_IDS = {
		'BidReceived': 'ItemID',
		'FeedbackReceived': 'FeedbackID',
		'ItemLost': 'ItemID',
		'ItemSold': 'ItemID',
		'ItemUnsold': 'ItemID',
		'ItemWon': 'ItemID',
		'MyMessagesM2MMessage': 'MessageID',
		'MyMessagesHighPriorityMessage': 'MessageID',
		'OutBid': 'ItemID',
		'TokenRevocation': '?',
	}

	def __init__(self, client, soap_action, post_data):
		self.client = client
		self.soap_action = soap_action
		self.data = post_data

		# parse message
		self.envelope = parseString(self.data).getElementsByTagName('soapenv:Envelope')[0]
		self.header = self.envelope.getElementsByTagName('soapenv:Header')[0]
		self.credentials = self.envelope.getElementsByTagName('ebl:RequesterCredentials')[0]
		self.signature = self.credentials.getElementsByTagName('ebl:NotificationSignature')[0].childNodes[0].data
		self.body = self.envelope.getElementsByTagName('soapenv:Body')[0]
		self.response = self.body.getElementsByTagName(self._SOAP_ACTION_RESPONSES[soap_action])[0]
		
		current_tag = self.response
		for tag in self._SOAP_ACTION_WRAPPERS[soap_action].split('.'):
			current_tag = current_tag.getElementsByTagName(tag)[0]
		self.wrapper = current_tag
		
		self.timestamp = self.response.getElementsByTagName('Timestamp')[0].childNodes[0].data
		self.ack = self.response.getElementsByTagName('Ack')[0].childNodes[0].data

	def get_recipient_name(self):
		if self.ack == 'Success':
			return self.response.getElementsByTagName('RecipientUserID')[0].childNodes[0].data
			
		else:
			return None
	
	def get_sender_name(self):
		if self.ack == 'Success':
			sender_tag = self._SOAP_ACTION_SENDERS[self.soap_action]
			current_tag = self.wrapper
			
			if sender_tag:
				for tag in sender_tag.split('.'):
					current_tag = current_tag.getElementsByTagName(tag)[0]
			
				return current_tag.childNodes[0].data
			
			else:
				return None
		
		else:
			return None
	
	def get_ebay_id(self):
		if self.ack == 'Success':
			return self.wrapper.getElementsByTagName(self._SOAP_ACTION_IDS[self.soap_action])[0].childNodes[0].data
			
		else:
			return None
	
	def get_tag(self, tag):
		if self.ack == 'Success':
			current_tag = self.wrapper
			not_found = False
			logging.debug('tag split: %s' % tag.split('.'))
			for tag_atom in tag.split('.'):
				try:
					current_tag = current_tag.getElementsByTagName(tag_atom)[0]
				except:
					not_found = True
					break
			
			if not_found:
				return None
			else:
				return current_tag.childNodes[0].data
		
		else:
			return None

	def verify_signature(self):
		if self.ack == 'Success':
			return self.client.verify_signature(self.signature, self.timestamp)
			
		else:
			return None

if __name__ == '__main__':
	import doctest
	doctest.testmod()