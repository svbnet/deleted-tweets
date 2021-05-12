from twython import Twython

class CredentialsBag:    
    def update_consumer(self, key, secret):
        self.consumer_key = key
        self.consumer_secret = secret
        return self
    
    def update_account(self, token, secret, account_id=None):
        self.access_token = token
        self.access_token_secret = secret
        self.account_id = account_id
        return self
    
    def create_twython(self):
        if self.access_token and self.access_token_secret:
            return Twython(self.consumer_key, self.consumer_secret,
                self.access_token, self.access_token_secret)
        else:
            return Twython(self.consumer_key, self.consumer_secret)
