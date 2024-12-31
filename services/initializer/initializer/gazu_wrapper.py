import gazu


class GazuWrapper:

    @staticmethod
    def login(server, login, password):
        gazu.client.set_host(server)
        gazu.set_host(server)
        gazu.log_in(login, password)

    @staticmethod
    def __getattr__(self, name):
        """
        Redirects attribute access to the inner module.

        Args:
            name (str): The name of the attribute being accessed.

        Returns:
            Any: The attribute from the wrapped module.
        """
        # Redirect attribute access to the wrapped module
        try:
            # Test Call for authentication
            gazu.project.all_open_projects()
        except gazu.exception.NotAuthenticatedException:
            gazu.refresh_token()

        if hasattr(gazu, name):
            return getattr(gazu, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
