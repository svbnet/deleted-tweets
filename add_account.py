from twython import Twython
from twython.exceptions import TwythonAuthError

import context

config = context.get_config()

consumer_keys = config.get('consumer', None)
if not consumer_keys:
    print('''\nPlease set the consumer keys in config.json as:
{
    "consumer": {
        "key": "<your_consumer_key_here>",
        "secret": "<your_consumer_secret_here>"
    }
    ...
}\n''')
    exit(1)
ck = consumer_keys['key']
cs = consumer_keys['secret']

rest = Twython(ck, cs)
try:
    auth = rest.get_authentication_tokens()
except TwythonAuthError:
    print("Bad API keys")
    exit(1)

print("\nGo to this URL and log in:\n" + auth['auth_url'] + "\n")

rest = Twython(ck, cs, auth['oauth_token'], auth['oauth_token_secret'])
pin = input('Enter PIN code: ')
try:
    tokens = rest.get_authorized_tokens(pin)
    access_token = tokens['oauth_token']
    access_token_secret = tokens['oauth_token_secret']
except TwythonAuthError:
    print("Invalid or expired PIN")
    exit(1)

rest = Twython(ck, cs, access_token, access_token_secret)
print('Adding account...')
account = rest.verify_credentials()

accounts = config.get('accounts', [])
accounts.append({
    'id': account['id_str'],
    'handle': account['screen_name'],
    'access': {
        'token': access_token,
        'secret': access_token_secret,
    },
})
config['accounts'] = accounts
context.commit_config()

print(f"Added account {account['screen_name']} ({account['id_str']})!")
