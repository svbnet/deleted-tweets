
class Retryer:
    def __init__(self, attempt_callback=None, exception_callback=None):
        self.attempt_callback = attempt_callback
        self.exception_callback = exception_callback
        self.succeeded = None
    
    def attempt(self, fn, max_attempts=10):
        attempts = 0
        while attempts < max_attempts:
            try:
                attempts += 1
                if self.attempt_callback:
                    self.attempt_callback(attempts, max_attempts)
                retval = fn()
                self.succeeded = True
                return retval
            except Exception as ex:
                if self.exception_callback:
                    self.exception_callback(ex)
                self.succeeded = False
