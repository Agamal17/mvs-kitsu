import gazu


class GazuWrapperType(type):
    def __getattr__(cls, name):
        try:
            # Test Call for authentication
            gazu.project.all_open_projects()
        except gazu.exception.NotAuthenticatedException:
            gazu.refresh_token()

        if hasattr(gazu, name):
            return getattr(gazu, name)
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")


class GazuWrapper(metaclass=GazuWrapperType):

    @classmethod
    def login(cls, server, login, password):
        gazu.client.set_host(server)
        gazu.set_host(server)
        gazu.log_in(login, password)