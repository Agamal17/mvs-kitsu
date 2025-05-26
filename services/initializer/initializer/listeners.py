import time

from .utils import (
    create_or_update_asset,
    create_or_update_concept,
    create_or_update_edit,
    create_or_update_episode,
    create_or_update_person,
    create_or_update_sequence,
    create_or_update_shot,
    create_or_update_task,
    delete_asset,
    delete_concept,
    delete_edit,
    delete_episode,
    delete_person,
    delete_project,
    delete_sequence,
    delete_shot,
    delete_task,
    update_project,
)
from .fullsync import full_sync
import gazu
import ayon_api
import multiprocessing


def run_listeners(listener_process, *args):
    retry_interval = 1
    while True:
        gazu_listener_process = multiprocessing.Process(target=listener_process, args=args)
        gazu_listener_process.start()
        gazu_listener_process.join(timeout=60 * 60 * 24)
        if gazu_listener_process.is_alive():
            gazu_listener_process.terminate()
            gazu_listener_process.join()
            time.sleep(retry_interval)
            retry_interval = min(retry_interval * 2, 3600)
        else:
            retry_interval = 1


class Listener:
    """Host Kitsu listener."""

    def __init__(self, addon):
        """Create client and add listeners to events without starting it.

        Args:
            login (str): Kitsu user login
            password (str): Kitsu user password

        """
        self.addon = addon
        self.settings = ayon_api.get_service_addon_settings()
        email_sercret = self.settings.get("login_email")
        password_secret = self.settings.get("login_password")
        self.kitsu_server_url = self.settings.get("server").rstrip("/") + "/api"
        self.kitsu_login_email = ayon_api.get_secret(email_sercret)["value"]
        self.kitsu_login_password = ayon_api.get_secret(password_secret)["value"]

        listener_process = multiprocessing.Process(target=run_listeners, args=(
            self.run_gazu_listeners, self.addon, self.kitsu_server_url, self.kitsu_login_email,
            self.kitsu_login_password
        )
                                                   )
        listener_process.start()

    @staticmethod
    def run_gazu_listeners(addon, url, login, password):
        gazu.client.set_host(url)
        gazu.set_host(url)
        gazu.log_in(login, password)
        gazu.refresh_access_token()

        gazu.set_event_host(
            url.replace("api", "socket.io")
        )
        event_client = gazu.events.init(logger=True, reconnection=False)

        gazu.events.add_listener(
            event_client, "project:new", lambda data: full_sync(addon, data)
        )
        gazu.events.add_listener(
            event_client, "project:update", lambda data: update_project(addon, data)
        )
        gazu.events.add_listener(
            event_client, "project:delete", lambda data: delete_project(addon, data)
        )

        gazu.events.add_listener(
            event_client, "asset:new", lambda data: create_or_update_asset(addon, data)
        )
        gazu.events.add_listener(
            event_client, "asset:update", lambda data: create_or_update_asset(addon, data)
        )
        gazu.events.add_listener(
            event_client, "asset:delete", lambda data: delete_asset(addon, data)
        )

        gazu.events.add_listener(
            event_client, "episode:new", lambda data: create_or_update_episode(addon, data)
        )
        gazu.events.add_listener(
            event_client, "episode:update", lambda data: create_or_update_episode(addon, data)
        )
        gazu.events.add_listener(
            event_client, "episode:delete", lambda data: delete_episode(addon, data)
        )

        gazu.events.add_listener(
            event_client, "sequence:new", lambda data: create_or_update_sequence(addon, data)
        )
        gazu.events.add_listener(
            event_client, "sequence:update", lambda data: create_or_update_sequence(addon, data)
        )
        gazu.events.add_listener(
            event_client, "sequence:delete", lambda data: delete_sequence(addon, data)
        )

        gazu.events.add_listener(
            event_client, "shot:new", lambda data: create_or_update_shot(addon, data)
        )
        gazu.events.add_listener(
            event_client, "shot:update", lambda data: create_or_update_shot(addon, data)
        )
        gazu.events.add_listener(
            event_client, "shot:delete", lambda data: delete_shot(addon, data)
        )
        try:
            gazu.events.add_listener(
                event_client, "edit:new", lambda data: create_or_update_edit(addon, data)
            )
            gazu.events.add_listener(
                event_client, "edit:update", lambda data: create_or_update_edit(addon, data)
            )
            gazu.events.add_listener(
                event_client, "edit:delete", lambda data: delete_edit(addon, data)
            )
        except:
            pass

        try:
            gazu.events.add_listener(
                event_client, "concept:new", lambda data: create_or_update_concept(addon, data)
            )
            gazu.events.add_listener(
                event_client, "concept:update", lambda data: create_or_update_concept(addon, data)
            )
            gazu.events.add_listener(
                event_client, "concept:delete", lambda data: delete_concept(addon, data)
            )

        except:
            pass

        gazu.events.add_listener(
            event_client, "task:new", lambda data: create_or_update_task(addon, data)
        )
        gazu.events.add_listener(
            event_client, "task:update", lambda data: create_or_update_task(addon, data)
        )
        gazu.events.add_listener(
            event_client, "task:delete", lambda data: delete_task(addon, data)
        )

        gazu.events.add_listener(
            event_client, "person:new", lambda data: create_or_update_person(addon, data)
        )
        gazu.events.add_listener(
            event_client, "person:update", lambda data: create_or_update_person(addon, data)
        )
        gazu.events.add_listener(
            event_client, "person:delete", lambda data: delete_person(addon, data)
        )

        """Start listening for events."""

        gazu.events.run_client(event_client)
