import json
import time

from pydantic import BaseModel
from typing import Any, Literal, get_args, TYPE_CHECKING
import httpx
from nxtools import logging

from ayon_server.entities import FolderEntity, TaskEntity, ProjectEntity, UserEntity
from ayon_server.lib.postgres import Postgres
from .constants import (
    CONSTANT_KITSU_MODELS,
)

from ayon_server.helpers.deploy_project import anatomy_to_project_data
from .anatomy import parse_attrib, get_kitsu_project_anatomy
from .utils import (
    get_folder_by_kitsu_id,
    get_user_by_kitsu_id,
    get_task_by_kitsu_id,
    create_folder, update_folder, delete_folder,
    create_task, update_task, delete_task,
    calculate_end_frame,
)

if TYPE_CHECKING:
    from .. import KitsuAddon

EntityDict = dict[str, Any]

KitsuEntityType = Literal[
    "Folder",
    "Asset",
    "Shot",
    "Sequence",
    "Episode",
    "Edit",
    "Concept",
    "Task",
    "Person",
    "Project",
]


class deleteEntitiesRequestModel(BaseModel):
    project_name: str
    entities: list[EntityDict]


class PushEntitiesRequestModel(BaseModel):
    project_name: str
    entities: list[EntityDict]


async def get_root_folder_id(
        user: "UserEntity",
        project_name: str,
        kitsu_type: KitsuEntityType,
        kitsu_type_id: str,
        subfolder_id: str | None = None,
        subfolder_name: str | None = None,
) -> str:
    """
    Get the root folder ID for a given Kitsu type and ID.
    If a folder/subfolder does not exist, it will be created.
    """
    res = await Postgres.fetch(
        f"""
        SELECT id FROM project_{project_name}.folders
        WHERE data->>'kitsuId' = $1
        """,
        kitsu_type_id,
    )

    if res:
        id = res[0]["id"]
    else:
        folder = await create_folder(
            project_name=project_name,
            name=kitsu_type,
            data={"kitsuId": kitsu_type_id},
        )
        id = folder.id

    if not (subfolder_id or subfolder_name):
        return id

    res = await Postgres.fetch(
        f"""
        SELECT id FROM project_{project_name}.folders
        WHERE data->>'kitsuId' = $1
        """,
        subfolder_id,
    )

    if res:
        sub_id = res[0]["id"]
    else:
        sub_folder = await create_folder(
            project_name=project_name,
            name=subfolder_name,
            parent_id=id,
            data={"kitsuId": subfolder_id},
        )
        sub_id = sub_folder.id
    return sub_id


async def create_access_group(
        addon: "KitsuAddon",
        user: "UserEntity",
        entity_dict: "EntityDict",
        name: str | None = None,
):
    from ayon_server.auth.session import Session
    try:
        if not name:
            settings = await addon.get_studio_settings()
            name = settings.sync_settings.sync_users.access_group
        session = await Session.create(user)
        headers = {"Authorization": f"Bearer {session.token}"}
        # Check if group already exists
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:5000/api/accessGroups/_",
                headers=headers,
            )

        for group in response.json():
            if group["name"] == name:
                # access group already exists
                return

        # Create a new access group
        payload = json.dumps(
            {
                "create": {"enabled": False, "access_list": []},
                "read": {"enabled": False, "access_list": []},
                "update": {"enabled": False, "access_list": []},
                "publish": {"enabled": False, "access_list": []},
                "delete": {"enabled": False, "access_list": []},
                "attrib_read": {"enabled": False, "attributes": []},
                "attrib_write": {"enabled": False, "attributes": []},
                "endpoints": {"enabled": False, "endpoints": []},
            }
        )

        async with httpx.AsyncClient() as client:
            return await client.put(
                f"http://127.0.0.1:5000/api/accessGroups/{name}/_",
                content=payload,
                headers=headers,
            )
    except Exception as e:
        print(e)


def match_ayon_roles_with_kitsu_role(role: str) -> dict[str, bool] | None:
    match role:
        case "admin":
            return {
                "isAdmin": True,
                "isManager": False,
            }
        case "manager":
            return {
                "isAdmin": False,
                "isManager": True,
            }
        case "user":
            return {
                "isAdmin": False,
                "isManager": False,
            }
        case _:
            return


async def generate_user_settings(
        addon: "KitsuAddon",
        entity_dict: "EntityDict",
):
    settings = await addon.get_studio_settings()
    data: dict[str, str] = {}
    match entity_dict["role"]:
        case "admin":  # Studio manager
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.admin
            )
        case "vendor":  # Vendor
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.vendor
            )
        case "client":  # Client
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.client
            )
        case "manager":  # Manager
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.manager
            )
        case "supervisor":  # Supervisor
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.supervisor
            )
        case "user":  # Artist
            data = match_ayon_roles_with_kitsu_role(
                settings.sync_settings.sync_users.roles.user
            )
    return data | {
        "data": {
            "defaultAccessGroups": [settings.sync_settings.sync_users.access_group],
        },
    }


async def sync_person(
    addon: "KitsuAddon",
    user: "UserEntity",
    existing_users: dict[str, Any],
    entity_dict: "EntityDict",
):

    username = entity_dict['desktop_login']
    entity_id = entity_dict['id']

    payload = {
        "name": username,
        "attrib": {
            "fullName": entity_dict.get("full_name", ""),
            "email": entity_dict.get("email", ""),
        },
    } | await generate_user_settings(
        addon,
        entity_dict,
    )

    payload["data"]["kitsuId"] = entity_id

    try:
        await UserEntity.load(username)
    except:
        pass
    else:
        return

    try:
        new_user = UserEntity(payload)
        settings = await addon.get_studio_settings()
        new_user.set_password(settings.sync_settings.sync_users.default_password)
        await new_user.save()
    except:
        logging.info(f"Couldn't create user {payload['name']}. It doesn't satisfy regex requirements")
    else:
        existing_users[entity_id] = username


async def sync_folder(
        addon: "KitsuAddon",
        user: "UserEntity",
        project: "ProjectEntity",
        existing_folders: dict[str, Any],
        entity_dict: "EntityDict",
):
    target_folder = await get_folder_by_kitsu_id(
        project.name,
        entity_dict["id"],
        existing_folders,
    )

    # Add description to attrib data
    data: dict[str, str | int | None] | None = entity_dict.get("data", {})
    # The value of key data might be None, in that case, create a new dict
    if data is None:
        data = {}
    if entity_dict.get("description"):
        data["description"] = entity_dict["description"]
    if target_folder is None:
        parent_folder = None
        if entity_dict["type"] == "Asset":
            if entity_dict.get("entity_type_id") in existing_folders:
                parent_id = existing_folders[entity_dict["entity_type_id"]]
            else:
                parent_id = await get_root_folder_id(
                    user=user,
                    project_name=project.name,
                    kitsu_type="Assets",
                    kitsu_type_id="asset",
                    subfolder_id=entity_dict["entity_type_id"],
                    subfolder_name=entity_dict["asset_type_name"],
                )
                existing_folders[entity_dict["entity_type_id"]] = parent_id
        elif entity_dict["type"] in get_args(KitsuEntityType):
            if entity_dict.get("parent_id") is None:
                parent_id = await get_root_folder_id(
                    user=user,
                    project_name=project.name,
                    kitsu_type=f"{entity_dict['type']}s",
                    kitsu_type_id=entity_dict["type"].lower(),
                )
            else:
                if entity_dict.get("parent_id") in existing_folders:
                    parent_id = existing_folders[entity_dict["parent_id"]]
                else:
                    parent_folder = await get_folder_by_kitsu_id(
                        project.name,
                        entity_dict["parent_id"],
                        existing_folders,
                    )
                    if parent_folder is None:
                        return
                    parent_id = parent_folder.id
        else:
            return
        # ensure folder type exists
        if entity_dict["type"] not in [f["name"] for f in project.folder_types]:
            project.folder_types.append(
                {"name": entity_dict["type"]}
                | CONSTANT_KITSU_MODELS.get(entity_dict["type"], {})
            )
            await project.save()

        if entity_dict['name'] is not None:
            if not parent_folder:
                parent_folder = await FolderEntity.load(project.name, parent_id)
            # Calculate the end-frame
            data["frame_out"] = calculate_end_frame(entity_dict, parent_folder)

            logging.info(f"Creating folder {entity_dict['name']}")
            target_folder = await create_folder(
                project_name=project.name,
                attrib=await parse_attrib(data),
                name=entity_dict["name"],
                folder_type=entity_dict["type"],
                parent_id=parent_id,
                data={"kitsuId": entity_dict["id"]},
            )
            existing_folders[entity_dict["id"]] = target_folder.id

    else:
        # Calculate the end-frame
        data["frame_out"] = calculate_end_frame(entity_dict, target_folder)
        changed = False
        if entity_dict['name'] is not None:
            changed = await update_folder(
                project_name=project.name,
                folder_id=target_folder.id,
                attrib=await parse_attrib(data),
                name=entity_dict["name"],
                folder_type=entity_dict["type"],
            )
        if changed:
            existing_folders[entity_dict["id"]] = target_folder.id


async def ensure_task_type(
        project: "ProjectEntity",
        task_type: dict,
) -> bool:
    """#TODO: kitsu listener for new task types would be preferable"""

    if task_type["name"].lower() not in [project_task_type["shortName"].lower() for project_task_type in project.task_types]:
        project.task_types.append(
            {
                "name": task_type["short_name"],
                "shortName": task_type['name'],
                "icon": "task_alt"
            }
        )
        await project.save()
        return True
    return False


async def ensure_task_status(
        project: "ProjectEntity",
        task_status: dict,
) -> bool:
    """#TODO: kitsu listener for new task statuses would be preferable"""

    if task_status['name'] not in [status["shortName"] for status in project.statuses]:
        project.statuses.append(
            {
                "name": task_status['short_name'],
                "shortName": task_status['name'],
                "color": task_status['color'],
            }
        )
        await project.save()
        return True
    return False


async def sync_task(
        addon: "KitsuAddon",
        user: "UserEntity",
        project: "ProjectEntity",
        existing_tasks: dict[str, Any],
        existing_folders: dict[str, Any],
        entity_dict: "EntityDict",
):
    if "task_status" in entity_dict:
        await ensure_task_status(project, entity_dict["task_status"])

    if "task_type" in entity_dict:
        await ensure_task_type(project, entity_dict["task_type"])

    else:
        return

    target_task = await get_task_by_kitsu_id(
        project.name,
        entity_dict["id"],
        existing_tasks,
    )

    if target_task is None:
        # Sync task
        if entity_dict.get("entity_id") in existing_folders:
            parent_id = existing_folders[entity_dict["entity_id"]]
        else:
            parent_folder = await get_folder_by_kitsu_id(
                project.name, entity_dict["entity_id"], existing_folders
            )

            if parent_folder:
                parent_id = parent_folder.id
            else:
                logging.info("Did not find parent folder")
                # The new task type haven't been implemented in Ayon yet
                return

        target_task = await create_task(
            project_name=project.name,
            folder_id=parent_id,
            status=entity_dict["task_status"]["short_name"],
            task_type=entity_dict["task_type"]["short_name"],
            name=entity_dict["name"],
            data={"kitsuId": entity_dict["id"]},
            assignees=entity_dict["assignees"],
        )
        existing_tasks[entity_dict["id"]] = target_task.id

    else:
        changed = await update_task(
            project_name=project.name,
            task_id=target_task.id,
            name=entity_dict.get("name", target_task.name),
            assignees=entity_dict.get("assignees", target_task.assignees),
            status=entity_dict['task_status'].get("short_name", target_task.status),
            task_type=entity_dict['task_type'].get("short_name", target_task.task_type),
        )
        if changed:
            existing_tasks[entity_dict["id"]] = target_task.id

async def sync_project(
    addon: "KitsuAddon",
    project: "ProjectEntity",
    entity_dict: "EntityDict",
):
    await addon.ensure_kitsu()
    anatomy = await get_kitsu_project_anatomy(addon, entity_dict['id'])
    anatomy_data = anatomy_to_project_data(anatomy)

    attr_whitelist=["task_types", "statuses"]

    project = await ProjectEntity.load(project.name)

    for key in attr_whitelist:
        if key in anatomy_data:
            for value in anatomy_data[key]:
                if value['name'] not in [x['name'] for x in getattr(project, key)]:
                    setattr(project, key, getattr(project, key) + [value])
            await project.save()

            original_list = getattr(project, key)
            for value in getattr(project, key):
                if value['name'] not in [x['name'] for x in anatomy_data[key]]:
                    setattr(project, key, [x for x in getattr(project, key) if x['name'] != value['name']])
            try:
                await project.save()
            except Exception as e:
                setattr(project, key, original_list)
                logging.warning(e)

    if "attrib" in anatomy_data:
        for key, value in anatomy_data["attrib"].items():
            if getattr(project.attrib, key) != value:
                setattr(project.attrib, key, value)
                if key not in project.own_attrib:
                    project.own_attrib.append(key)
        await project.save()


async def push_entities(
        addon: "KitsuAddon",
        user: "UserEntity",
        payload: PushEntitiesRequestModel,
) -> dict[str, dict[Any, Any]]:
    start_time = time.time()
    project = None
    if payload.project_name != "":
        project = await ProjectEntity.load(payload.project_name)

    # A mapping of kitsu entity ids to folder ids
    # they are added when a task or folder is created or updated and returned by the method - useful for testing

    # This object only exists during the request
    # and speeds up the process of finding folders
    # if multiple entities are requested to sync

    folders = {}
    tasks = {}
    users = {}

    for entity_dict in payload.entities:
        # required fields
        assert "type" in entity_dict
        assert "id" in entity_dict

        logging.info(
            f"entity_dict['type'] = {entity_dict['type']}"
        )
        if entity_dict["type"] not in get_args(KitsuEntityType):
            continue

        if entity_dict["type"] == "Project":
            await sync_project(addon, project, entity_dict)

        elif entity_dict["type"] == "Person":
            await sync_person(
                addon,
                user,
                users,
                entity_dict,
            )

        elif entity_dict["type"] != "Task":
            await sync_folder(
                addon,
                user,
                project,
                folders,
                entity_dict,
            )
        else:
            await sync_task(
                addon,
                user,
                project,
                tasks,
                folders,
                entity_dict,
            )

    logging.info(
        f"Synced {len(payload.entities)} entities in {time.time() - start_time}s"
    )


async def delete_entities(
        addon: "KitsuAddon",
        user: "UserEntity",
        payload: deleteEntitiesRequestModel,
) -> None:
    project = await ProjectEntity.load(payload.project_name)

    folders = {}
    tasks = {}

    for entity_dict in payload.entities:
        if entity_dict["type"] not in get_args(KitsuEntityType):
            continue

        if entity_dict["type"] == "Person":
            target_user = await get_user_by_kitsu_id(entity_dict["id"])
            if not target_user:
                continue

            await target_user.delete()

        elif entity_dict["type"] == "Task":
            task = await get_task_by_kitsu_id(
                project.name,
                entity_dict["id"],
                tasks,
            )
            if not task:
                continue

            await delete_task(
                project_name=project.name,
                task_id=task.id,
                user=user,
            )

        else:
            folder = await get_folder_by_kitsu_id(
                project.name,
                entity_dict["id"],
                folders,
            )
            if not folder:
                continue

            await delete_folder(
                project_name=project.name,
                folder_id=folder.id,
                user=user,
            )
