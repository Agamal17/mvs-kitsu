from .gazu_wrapper import GazuWrapper as gazu
import ayon_api
from nxtools import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sync_server import KitsuInitializer

def full_sync(parent: "KitsuInitializer", data):
    if isinstance(data, str):
        kitsu_project_id = data
    else:
        kitsu_project_id = data['project_id']

    project = gazu.project.get_project(kitsu_project_id)
    
    ayon_api.post(
        f"{parent.entrypoint}/sync",
        project_name = project['name'],
        project = project
    )
