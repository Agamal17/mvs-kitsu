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
import threading


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
        self.kitsu_server_url = self.settings.get("server").rstrip("/") + "/api"
        email_sercret = self.settings.get("login_email")
        password_secret = self.settings.get("login_password")
        self.kitsu_login_email = ayon_api.get_secret(email_sercret)["value"]
        self.kitsu_login_password = ayon_api.get_secret(password_secret)[
            "value"
        ]

        gazu.client.set_host(self.kitsu_server_url)
        gazu.set_host(self.kitsu_server_url)
        gazu.log_in(self.kitsu_login_email, self.kitsu_login_password)

        gazu.set_event_host(
            self.kitsu_server_url.replace("api", "socket.io")
        )
        self.event_client = gazu.events.init()

        gazu_listener_thread = threading.Thread(target=self.run_gazu_listeners)
        gazu_listener_thread.start()

    def run_gazu_listeners(self):
        gazu.events.add_listener(
            self.event_client, "project:new", lambda data: full_sync(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "project:update", lambda data: update_project(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "project:delete", lambda data: delete_project(self.addon, data)
        )

        gazu.events.add_listener(
            self.event_client, "asset:new", lambda data: create_or_update_asset(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "asset:update", lambda data: create_or_update_asset(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "asset:delete", lambda data: delete_asset(self.addon, data)
        )

        gazu.events.add_listener(
            self.event_client, "episode:new", lambda data: create_or_update_episode(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "episode:update", lambda data: create_or_update_episode(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "episode:delete", lambda data: delete_episode(self.addon, data)
        )

        gazu.events.add_listener(
            self.event_client, "sequence:new", lambda data: create_or_update_sequence(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "sequence:update", lambda data: create_or_update_sequence(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "sequence:delete", lambda data: delete_sequence(self.addon, data)
        )

        gazu.events.add_listener(
            self.event_client, "shot:new", lambda data: create_or_update_shot(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "shot:update", lambda data: create_or_update_shot(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "shot:delete", lambda data: delete_shot(self.addon, data)
        )
        try:
            gazu.events.add_listener(
                self.event_client, "edit:new", lambda data: create_or_update_edit(self.addon, data)
            )
            gazu.events.add_listener(
                self.event_client, "edit:update", lambda data: create_or_update_edit(self.addon, data)
            )
            gazu.events.add_listener(
                self.event_client, "edit:delete", lambda data: delete_edit(self.addon, data)
            )
        except:
            pass

        try:
            gazu.events.add_listener(
                self.event_client, "concept:new", lambda data: create_or_update_concept(self.addon, data)
            )
            gazu.events.add_listener(
                self.event_client, "concept:update", lambda data: create_or_update_concept(self.addon, data)
            )
            gazu.events.add_listener(
                self.event_client, "concept:delete", lambda data: delete_concept(self.addon, data)
            )

        except:
            pass

        gazu.events.add_listener(
            self.event_client, "task:new", lambda data: create_or_update_task(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "task:update", lambda data: create_or_update_task(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "task:delete", lambda data: delete_task(self.addon, data)
        )

        gazu.events.add_listener(
            self.event_client, "person:new", lambda data: create_or_update_person(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "person:update", lambda data: create_or_update_person(self.addon, data)
        )
        gazu.events.add_listener(
            self.event_client, "person:delete", lambda data: delete_person(self.addon, data)
        )

        """Start listening for events."""

        gazu.events.run_client(self.event_client)
