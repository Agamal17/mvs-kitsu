from typing import TYPE_CHECKING

import ayon_api
import gazu
from nxtools import logging

from .fullsync import full_sync
if TYPE_CHECKING:
    from .sync_server import KitsuInitializer


def update_project(parent: "KitsuInitializer", data: dict[str, str]):
    # Get asset entity
    entity = gazu.project.get_project(data["project_id"])
    project_name = entity['name']

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_project(parent: "KitsuInitializer", data: dict[str, str]):
    id = data['project_id']
    projects = ayon_api.get_project_names()
    for name in projects:
        project = ayon_api.get_project(name)
        if project['data']['kitsuProjectId'] == id:
            ayon_api.delete_project(name)


def create_or_update_asset(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']


    def preprocess_asset(
        kitsu_project_id: str,
        asset: dict[str, str],
    ) -> dict[str, str]:

        def get_asset_types(kitsu_project_id: str) -> dict[str, str]:
            raw_asset_types = gazu.asset.all_asset_types_for_project(kitsu_project_id)
            kitsu_asset_types = {}
            for asset_type in raw_asset_types:
                kitsu_asset_types[asset_type["id"]] = asset_type["name"]
            return kitsu_asset_types

        asset_types = get_asset_types(kitsu_project_id)

        if "entity_type_id" in asset and asset["entity_type_id"] in asset_types:
            asset["asset_type_name"] = asset_types[asset["entity_type_id"]]
        return asset


    # Get asset entity
    entity = gazu.asset.get_asset(data["asset_id"])
    entity = preprocess_asset(entity["project_id"], entity)


    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_asset(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["asset_id"],
        "type": "Asset"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_episode(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    # Get episode entity
    entity = gazu.shot.get_episode(data["episode_id"])

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_episode(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["episode_id"],
        "type": "Episode"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_sequence(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = gazu.shot.get_sequence(data["sequence_id"])


    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_sequence(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["sequence_id"],
        "type": "Sequence"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_shot(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = gazu.shot.get_shot(data["shot_id"])

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_shot(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["shot_id"],
        "type": "Shot"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def preprocess_task(
    kitsu_project_id: str,
    task: dict[str, str | list[str]],
    task_types: dict[str, str | list[str]] = {},
    statuses: dict[str, str] = {},
) -> dict[str, str | list[str]]:

    def get_task_types(project_id: str):
        raw_task_types = gazu.task.all_task_types_for_project(project_id)
        kitsu_task_types = {}
        for task_type in raw_task_types:
            kitsu_task_types[task_type["id"]] = task_type["name"]
        return kitsu_task_types

    def get_statuses():
        raw_statuses = gazu.task.all_task_statuses()
        kitsu_statuses = {}
        for status in raw_statuses:
            kitsu_statuses[status["id"]] = status["short_name"]
        return kitsu_statuses

    if not task_types:
        task_types = get_task_types(kitsu_project_id)

    if not statuses:
        statuses = get_statuses()

    if "task_type_id" in task and task["task_type_id"] in task_types:
        task["task_type_name"] = task_types[task["task_type_id"]]

    if "task_status_id" in task and task["task_status_id"] in statuses:
        task["task_status_name"] = statuses[task["task_status_id"]]

    if "name" in task and "task_type_name" in task and task["name"] == "main":
        task["name"] = task["task_type_name"].lower()

    # Match the assigned ayon user with the assigned kitsu email
    ayon_users = {
        user["attrib"]["email"]: user["name"] for user in ayon_api.get_users()
    }
    task_emails = {user["email"] for user in task["persons"]}
    task["assignees"] = []
    task["assignees"].extend(
        ayon_users[email] for email in task_emails if email in ayon_users
    )

    return task

def create_or_update_task(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = gazu.task.get_task(data["task_id"])
    entity = preprocess_task(entity["project_id"], entity)

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_task(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["task_id"],
        "type": "Task"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_edit(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    # Get edit entity
    entity = gazu.edit.get_edit(data["edit_id"])


    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_edit(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["edit_id"],
        "type": "Edit"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_concept(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    # Get concept entity
    entity = gazu.concept.get_concept(data["concept_id"])

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name=project_name,
        entities=[entity],
    )


def delete_concept(parent: "KitsuInitializer", data: dict[str, str]):
    project_name = gazu.project.get_project(data["project_id"])['name']

    entity = {
        "id": data["concept_id"],
        "type": "Concept"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name=project_name,
        entities=[entity],
    )


def create_or_update_person(parent: "KitsuInitializer", data: dict[str, str]):
    entity = gazu.person.get_person(data["person_id"])

    return ayon_api.post(
        f"{parent.entrypoint}/push",
        project_name="",
        entities=[entity],
    )


def delete_person(parent: "KitsuInitializer", data: dict[str, str]):
    entity = {
        "id": data["person_id"],
        "type": "Person"
    }

    return ayon_api.post(
        f"{parent.entrypoint}/remove",
        project_name="",
        entities=[entity],
    )