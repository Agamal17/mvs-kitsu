from typing import TYPE_CHECKING
from pydantic import BaseModel
from .pushing import push_entities, PushEntitiesRequestModel
from ayon_server.lib.postgres import Postgres
from nxtools import logging
from .anatomy import get_kitsu_project_anatomy
from .init_pairing import init_pairing, InitPairingRequest
from ayon_server.helpers.deploy_project import create_project_from_anatomy

if TYPE_CHECKING:
    from .. import KitsuAddon

currently_syncing: list[str] = []


class syncProjectModel(BaseModel):
    project_name: str
    project: dict = {}


def preprocess_asset(
        asset,
        asset_types={},
):
    if "entity_type_id" in asset and asset["entity_type_id"] in asset_types:
        asset["asset_type_name"] = asset_types[asset["entity_type_id"]]
    return asset


async def preprocess_task(
        task,
        task_types={},
        statuses={},
):
    if "task_type_id" in task and task["task_type_id"] in task_types:
        task["task_type"] = task_types[task["task_type_id"]]

    if "task_status_id" in task and task["task_status_id"] in statuses:
        task["task_status"] = statuses[task["task_status_id"]]

    if "name" in task and "task_type" in task and task["name"] == "main":
        task["name"] = task["task_type"]['name'].lower()

    # Match the assigned ayon user with the assigned kitsu email

    users = await Postgres.fetch("SELECT * FROM users where attrib ->> 'email' is not null")
    ayon_users = {
        user["attrib"]["email"]: user["name"] for user in users
    }
    task_emails = {user["email"] for user in task["persons"]}
    task["assignees"] = []
    task["assignees"].extend(
        ayon_users[email] for email in task_emails if email in ayon_users
    )

    return task


async def sync_project(
        addon: "KitsuAddon",
        user,
        project_name: str,
        project_dict: dict
):
    if project_name == "":
        persons = await addon.kitsu.get('/data/persons')
        entities = persons
    else:
        if project_dict['id'] in currently_syncing:
            logging.info(f"Currently syncing: {project_name}")
            return
        else:
            currently_syncing.append(project_dict['id'])
        try:
            project_code = project_dict.get("code", project_name.replace(" ", "_"))
            payload = InitPairingRequest(project_name=project_name, project_code=project_code,
                                         project_id=project_dict["id"])
            await init_pairing(addon, user, payload)

        except:
            pass

        project = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}')

        raw_asset_types = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/asset-types')
        asset_types = {}
        for asset_type in raw_asset_types:
            asset_types[asset_type["id"]] = asset_type["name"]

        raw_statuses = await addon.kitsu.get(f'/data/task-status')
        task_statuses = {}
        for status in raw_statuses:
            task_statuses[status["id"]] = {"name": status["name"], "short_name": status["short_name"],
                                           "color": status["color"]}

        raw_task_types = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/task-types')
        task_types = {}
        for task_type in raw_task_types:
            task_types[task_type["id"]] = {"name": task_type["name"], "short_name": task_type["short_name"]}

        episodes = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/episodes')
        sequences = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/sequences')
        shots = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/shots')
        try:
            edits = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/edits')
        except:
            edits = []
        try:
            concepts = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/concepts')
        except:
            concepts = []

        tasks = []
        raw_tasks = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/tasks')
        for record in raw_tasks:
            record["persons"] = []
            for id in record["assignees"]:
                person = await addon.kitsu.get('data/persons', params={"id": id, "relations": False})
                record["persons"].append({"email": person[0]["email"]})
            tasks.append(
                await preprocess_task(record, task_types, task_statuses)
            )

        assets = []
        raw_assets = await addon.kitsu.get(f'/data/projects/{project_dict["id"]}/assets')
        for record in raw_assets:
            assets.append(preprocess_asset(record, asset_types))

        entities = [project] + assets + episodes + sequences + shots + edits + concepts + tasks

    payload = PushEntitiesRequestModel(project_name=project_name, entities=entities)

    try:
        await push_entities(
            addon,
            user,
            payload
        )

    except Exception as e:
        logging.error(f"Error syncing project {project_name}: {e}")
        raise e

    finally:
        if project_dict.get("id") in currently_syncing:
            currently_syncing.remove(project_dict["id"])

    return logging.info(f"Successfuly synced {project_name}") if project_name else logging.info(
        "Successfuly synced persons")
