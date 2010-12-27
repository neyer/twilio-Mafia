import twilio

ACCOUNT_SID = 'AC7c1a9aec8e88ea52020cf1ddc502adca'
AUTH_TOKEN = '4980d02b59b52245f6d0a5c654c99927'
FROM_NUMBER = '+18302679954'



def make_call(phone_number,twiml_url):
    api_call = '/2010-04-01/Accounts/%s/Calls' % ACCOUNT_SID  
    xml = twilio.Account(ACCOUNT_SID,
        AUTH_TOKEN).request(api_call,
		          method='POST',
                          vars={'From':FROM_NUMBER,
    		                 'To' : phone_number,
                                 'Url': twiml_url})


def send_sms(phone_number, message):
    api_call = '/2010-04-01/Accounts/%s/SMS/Messages' % ACCOUNT_SID  
    xml = twilio.Account(ACCOUNT_SID,
			AUTH_TOKEN).request(api_call,
					    method='POST',
					    vars={'From':FROM_NUMBER,
						  'To': phone_number,
					          'Body' : message})
		     
