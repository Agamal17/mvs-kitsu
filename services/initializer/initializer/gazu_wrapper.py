import gazu


class GazuWrapperType(type):
    def __getattr__(cls, name):
        if hasattr(gazu, name):
            try:
                res = getattr(gazu, name)
            except gazu.exception.NotAuthenticatedException:
                gazu.refresh_access_token()
                res = getattr(gazu, name)
            return res

        raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")


class GazuWrapper(metaclass=GazuWrapperType):

    @classmethod
    def login(cls, server, login, password):
        gazu.client.set_host(server)
        gazu.set_host(server)
        gazu.log_in(login, password)
