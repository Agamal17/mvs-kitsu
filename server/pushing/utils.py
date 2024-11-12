from nxtools import logging
import re
import unicodedata
from typing import Any
from nxtools import slugify
from ayon_server.lib.postgres import Postgres
from ayon_server.entities import (
    FolderEntity,
    TaskEntity,
    UserEntity,
)

async def get_user_by_kitsu_id(
        kitsu_id: str,
) -> UserEntity | None:
    """Get an Ayon UserEndtity by its Kitsu ID"""
    res = await Postgres.fetch(
        "SELECT name FROM public.users WHERE data->>'kitsuId' = $1",
        kitsu_id,
    )
    if not res:
        return None
    user = await UserEntity.load(res[0]["name"])
    return user

async def get_folder_by_kitsu_id(
    project_name: str,
    kitsu_id: str,
    existing_folders: dict[str, str] | None = None,
) -> FolderEntity:
    """Get an Ayon FolderEndtity by its Kitsu ID"""

    if existing_folders and (kitsu_id in existing_folders):
        folder_id = existing_folders[kitsu_id]

    else:
        res = await Postgres.fetch(
            f"""
            SELECT id FROM project_{project_name}.folders
            WHERE data->>'kitsuId' = $1
            """,
            kitsu_id,
        )
        if not res:
            return None
        folder_id = res[0]["id"]
        existing_folders[kitsu_id] = folder_id

    return await FolderEntity.load(project_name, folder_id)

    return None

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def create_short_name(name: str) -> str:
    code = name.lower()

    if "_" in code:
        subwords = code.split("_")
        code = "".join([subword[0] for subword in subwords])[:4]
    elif len(name) > 4:
        vowels = ["a", "e", "i", "o", "u"]
        filtered_word = "".join([char for char in code if char not in vowels])
        code = filtered_word[:4]

    # if there is a number at the end of the code, add it to the code
    last_char = code[-1]
    if last_char.isdigit():
        code += last_char

    return code


def create_name_and_label(kitsu_name: str) -> dict[str, str]:
    """From a name coming from kitsu, create a name and label"""
    name_slug = slugify(kitsu_name, separator="_")
    return {"name": name_slug, "label": kitsu_name}

async def get_user_by_kitsu_id(
    kitsu_id: str,
) -> UserEntity | None:
    """Get an Ayon UserEndtity by its Kitsu ID"""
    res = await Postgres.fetch(
        "SELECT name FROM public.users WHERE data->>'kitsuId' = $1",
        kitsu_id,
    )
    if not res:
        return None
    user = await UserEntity.load(res[0]["name"])
    return user

async def get_task_by_kitsu_id(
    project_name: str,
    kitsu_id: str,
    existing_tasks: dict[str, str] | None = None,
) -> TaskEntity:
    """Get an Ayon TaskEntity by its Kitsu ID"""

    if existing_tasks and (kitsu_id in existing_tasks):
        folder_id = existing_tasks[kitsu_id]

    else:
        res = await Postgres.fetch(
            f"""
            SELECT id FROM project_{project_name}.tasks
            WHERE data->>'kitsuId' = $1
            """,
            kitsu_id,
        )
        if not res:
            return None
        folder_id = res[0]["id"]
        existing_tasks[kitsu_id] = folder_id

    return await TaskEntity.load(project_name, folder_id)



async def create_task(
    project_name: str,
    name: str,
    attrib: dict[str, Any] | None = None,
    **kwargs,
) -> TaskEntity:

    # ensure name is correctly formatted
    if name:
        name = to_entity_name(name)


    task = TaskEntity(
        project_name=project_name,
        payload=dict(kwargs, name=name),
    )
    await task.save()

    return task


def calculate_end_frame(
    entity_dict: dict[str, int], folder: FolderEntity
) -> int | None:
    # for concepts data=None
    if "data" not in entity_dict or not isinstance(entity_dict["data"], dict):
        return

    # return end-frame if set
    if entity_dict["data"].get("frame_out"):
        return entity_dict["data"].get("frame_out")

    # Calculate the end-frame
    if entity_dict.get("nb_frames") and not entity_dict["data"].get("frame_out"):
        frame_start = entity_dict["data"].get("frame_in")
        # If kitsu doesn't have a frame in, get it from the folder in Ayon
        if frame_start is None and hasattr(folder.attrib, "frameStart"):
            frame_start = folder.attrib.frameStart
        if frame_start is not None:
            return int(frame_start) + int(entity_dict["nb_frames"])

def to_entity_name(kitsu_name) -> str:
    """ convert kitsu names so they will pass Ayon Entity name validation """
    name = kitsu_name.strip()
    # replace whitespace
    name = re.sub(r'\s+', "_", name)
    # remove any invalid characters
    name = re.sub(r'[^a-zA-Z0-9_\.\-]', '', name)
    return name


async def create_folder(
    project_name: str,
    name: str,
    attrib: dict[str, Any] | None = None,
    **kwargs,
) -> FolderEntity:
    """
    TODO: This is a re-implementation of create folder, which does not
    require background tasks. Maybe just use the similar function from
    api.folders.folders.py?
    """
    # ensure name is correctly formatted
    folder = None
    try:
        folder = FolderEntity(
            project_name=project_name,
            payload=dict(kwargs, name=name),
        )
        await folder.save()
    except Exception as e:
        if name == "Sequences":
            res = await Postgres.fetch(
                f"""
                SELECT id FROM project_{project_name}.folders
                WHERE name = $1
                """,
                name,
            )
            res = res[0]['id']
            folder = await FolderEntity.load(project_name, res)
            folder.data['kitsuId'] = kwargs['data']['kitsuId']
            await folder.save()
        else:
            res = await Postgres.fetch(
                f"""
                SELECT id FROM project_{project_name}.folders
                WHERE name = $1 AND parent_id = $2
                """,
                name, kwargs['parent_id']
            )
            res = res[0]['id']
            folder = await FolderEntity.load(project_name, res)
            folder.data['kitsuId'] = kwargs['data']['kitsuId']
            await folder.save()

    return folder


async def update_folder(
    project_name: str,
    folder_id: str,
    name: str,
    **kwargs,
) -> bool:
    folder = await FolderEntity.load(project_name, folder_id)

    payload: dict[str, Any] = {**kwargs}
    folder.name = name

    for key, value in payload["attrib"].items():
        if getattr(folder.attrib, key) != value:
            setattr(folder.attrib, key, value)
            if key not in folder.own_attrib:
                folder.own_attrib.append(key)

    await folder.save()


async def create_task(
    project_name: str,
    name: str,
    **kwargs,
) -> TaskEntity:
    payload = {**kwargs, **create_name_and_label(name)}
    task = TaskEntity(
        project_name=project_name,
        payload=payload,
    )

    await task.save()

    return task


async def update_task(
    project_name: str,
    task_id: str,
    name: str,
    **kwargs,
) -> bool:
    task = await TaskEntity.load(project_name, task_id)
    changed = False

    payload = {**kwargs, **create_name_and_label(name)}

    # keys that can be updated
    for key in ["name", "label", "status", "task_type", "assignees"]:
        if key in payload and getattr(task, key) != payload[key]:
            setattr(task, key, payload[key])
            changed = True
    if "attrib" in payload:
        for key, value in payload["attrib"].items():
            if getattr(task.attrib, key) != value:
                setattr(task.attrib, key, value)
                if key not in task.own_attrib:
                    task.own_attrib.append(key)
                changed = True
    if changed:
        await task.save()

    return changed

async def delete_folder(
    project_name: str,
    folder_id: str,
    user: "UserEntity",
    **kwargs,
) -> None:
    folder = await FolderEntity.load(project_name, folder_id)

    await folder.delete(force = True)


async def delete_task(
    project_name: str,
    task_id: str,
    user: "UserEntity",
    **kwargs,
) -> None:
    task = await TaskEntity.load(project_name, task_id)

    await task.delete()