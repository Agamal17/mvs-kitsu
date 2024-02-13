import os
import socket
import sys
import threading
import time

import ayon_api
import gazu
from nxtools import log_traceback, logging

from .fullsync import full_sync
from .update_from_kitsu import (
    create_or_update_asset,
    create_or_update_concept,
    create_or_update_edit,
    create_or_update_episode,
    create_or_update_sequence,
    create_or_update_shot,
    create_or_update_task,
    delete_asset,
    delete_concept,
    delete_edit,
    delete_episode,
    delete_sequence,
    delete_shot,
    delete_task,
)

if service_name := os.environ.get("AYON_SERVICE_NAME"):
    logging.user = service_name

SENDER = f"kitsu-processor-{socket.gethostname()}"


class KitsuServerError(Exception):
    pass


class KitsuSettingsError(Exception):
    pass


class KitsuProcessor:
    def __init__(self):
        #
        # Connect to Ayon
        #
        try:
            # ayon_api.init_service(addon_name='kitsu', addon_version='1.0.2-dev1', service_name='processor')
            ayon_api.init_service()
            connected = True
        except Exception:
            log_traceback()
            connected = False

        if not connected:
            time.sleep(10)
            print("KitsuProcessor failed to connect to Ayon")
            sys.exit(1)

        #
        # Load settings and stuff...
        #

        self.addon_name = ayon_api.get_service_addon_name()
        self.addon_version = ayon_api.get_service_addon_version()
        self.settings = ayon_api.get_service_addon_settings()
        self.entrypoint = f"/addons/{self.addon_name}/{self.addon_version}"

        #
        # Get list of projects that have been paired
        #
        self.pairing_list = self.get_pairing_list()

        #
        # Get Kitsu server credentials from settings
        #

        try:
            self.kitsu_server_url = self.settings.get("server").rstrip("/") + "/api"

            email_sercret = self.settings.get("login_email")
            password_secret = self.settings.get("login_password")

            assert email_sercret, f"Email secret `{email_sercret}` not set"
            assert password_secret, f"Password secret `{password_secret}` not set"

            try:
                self.kitsu_login_email = ayon_api.get_secret(email_sercret)["value"]
                self.kitsu_login_password = ayon_api.get_secret(password_secret)[
                    "value"
                ]
            except KeyError as e:
                raise KitsuSettingsError(f"Secret `{e}` not found") from e

            assert self.kitsu_login_password, "Kitsu password not set"
            assert self.kitsu_server_url, "Kitsu server not set"
            assert self.kitsu_login_email, "Kitsu email not set"
        except AssertionError as e:
            logging.error(f"KitsuProcessor failed to initialize: {e}")
            raise KitsuSettingsError() from e

        #
        # Connect to Kitsu
        #
        gazu.set_host(self.kitsu_server_url)
        if not gazu.client.host_is_valid():
            raise KitsuServerError(
                f"Kitsu server `{self.kitsu_server_url}` is not valid"
            )

        try:
            gazu.log_in(self.kitsu_login_email, self.kitsu_login_password)
            logging.info(f"Gazu logged in as {self.kitsu_login_email}")
        except gazu.exception.AuthFailedException as e:
            raise KitsuServerError(f"Kitsu login failed: {e}") from e

        # init event client
        self.kitsu_events_url = self.kitsu_server_url.replace("api", "socket.io")
        gazu.set_event_host(self.kitsu_events_url)
        self.event_client = gazu.events.init()

        # ============= Add Kitsu Event Listeners ==============
        gazu_listener_thread = threading.Thread(target=self.run_gazu_listeners)
        gazu_listener_thread.start()

    def run_gazu_listeners(self):
        # gazu.events.add_listener(
        #     self.event_client, "project:new", self._new_project
        # )
        # gazu.events.add_listener(
        #     self.event_client, "project:update", self._update_project
        # )
        # gazu.events.add_listener(
        #     self.event_client, "project:delete", self._delete_project
        # )

        gazu.events.add_listener(
            self.event_client,
            "asset:new",
            lambda data: create_or_update_asset(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "asset:update",
            lambda data: create_or_update_asset(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "asset:delete",
            lambda data: delete_asset(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "episode:new",
            lambda data: create_or_update_episode(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "episode:update",
            lambda data: create_or_update_episode(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "episode:delete",
            lambda data: delete_episode(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "sequence:new",
            lambda data: create_or_update_sequence(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "sequence:update",
            lambda data: create_or_update_sequence(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "sequence:delete",
            lambda data: delete_sequence(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "shot:new",
            lambda data: create_or_update_shot(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "shot:update",
            lambda data: create_or_update_shot(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "shot:delete",
            lambda data: delete_shot(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "task:new",
            lambda data: create_or_update_task(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "task:update",
            lambda data: create_or_update_task(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "task:delete",
            lambda data: delete_task(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "edit:new",
            lambda data: create_or_update_edit(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "edit:update",
            lambda data: create_or_update_edit(self, data),
        )
        gazu.events.add_listener(
            self.event_client,
            "edit:delete",
            lambda data: delete_edit(self, data),
        )
        # Currently concepts executes both concepts and assets
        # Talking to CGWire about this so they can fix it in Gazu
        # The code below works as intended so when CGWire
        # fixes the problem we can just uncomment this.
        # gazu.events.add_listener(
        #    self.event_client,
        #    "concept:new",
        #    lambda data: create_or_update_concept(self, data),
        # )
        # gazu.events.add_listener(
        #    self.event_client,
        #    "concept:update",
        #    lambda data: create_or_update_concept(self, data),
        # )
        # gazu.events.add_listener(
        #    self.event_client,
        #    "concept:delete",
        #    lambda data: delete_concept(self, data),
        # )
        logging.info("Gazu event listeners added")
        gazu.events.run_client(self.event_client)

    def get_pairing_list(self):
        """maintain a list of pairings so that we can check
        the kitsu change is in a paired project and get the ayon project name
        """
        logging.info("get_pairing_list")
        res = ayon_api.get(f"{self.entrypoint}/pairing")

        assert res.status_code == 200, f"{self.entrypoint}/pairing failed"
        # logging.info(f'get_pairing_list {res.status_code} {res.data}')
        return res.data

    def get_paired_ayon_project(self, kitsu_project_id: str) -> str | None:
        """returns the ayon project if paired else None"""
        for pair in self.pairing_list:
            if pair["kitsuProjectId"] == kitsu_project_id:
                return pair["ayonProjectName"]

    def set_paired_ayon_project(self, kitsu_project_id: str, ayon_project_name: str):
        """add a new pair to the list"""
        for pair in self.pairing_list:
            if "kitsuProjectId" in pair:
                return
        self.pairing_list.append(
            {"kitsuProjectId": kitsu_project_id, "ayonProjectName": ayon_project_name}
        )

    def start_processing(self):
        logging.info("KitsuProcessor started")

        while True:
            job = ayon_api.enroll_event_job(
                source_topic="kitsu.sync_request",
                target_topic="kitsu.sync",
                sender=SENDER,
                description="Syncing Kitsu to Ayon",
                max_retries=3,
            )

            if not job:
                time.sleep(5)
                continue

            src_job = ayon_api.get_event(job["dependsOn"])

            kitsu_project_id = src_job["summary"]["kitsuProjectId"]
            ayon_project_name = src_job["project"]

            ayon_api.update_event(
                job["id"],
                sender=SENDER,
                status="in_progress",
                project_name=ayon_project_name,
                description="Syncing Kitsu project...",
            )

            try:
                full_sync(self, kitsu_project_id, ayon_project_name)

                # if successful add the pair to the list
                self.set_paired_ayon_project(kitsu_project_id, ayon_project_name)
            except Exception:
                log_traceback(f"Unable to sync kitsu project {ayon_project_name}")

                ayon_api.update_event(
                    job["id"],
                    sender=SENDER,
                    status="failed",
                    project_name=ayon_project_name,
                    description="Sync failed",
                )
            else:
                ayon_api.update_event(
                    job["id"],
                    sender=SENDER,
                    status="finished",
                    project_name=ayon_project_name,
                    description="Kitsu sync finished",
                )

        logging.info("KitsuProcessor finished processing")
        gazu.log_out()
