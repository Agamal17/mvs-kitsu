from typing import TYPE_CHECKING
from pydantic import BaseModel
from ayon_server.entities import UserEntity
from ayon_server.exceptions import ConflictException
from ayon_server.helpers.deploy_project import create_project_from_anatomy
from ayon_server.lib.postgres import Postgres

from .anatomy import get_kitsu_project_anatomy

if TYPE_CHECKING:
    from .. import KitsuAddon


class InitPairingRequest(BaseModel):
    project_id: str
    project_name: str
    project_code: str
    # anatomy_preset: str | None = Field(None, title="Anatomy preset")

async def ensure_ayon_project_not_exists(project_name: str, project_code: str):
    async for res in Postgres.iterate(
        "SELECT name FROM projects WHERE name = $1 OR code = $2",
        project_name,
        project_code,
    ):
        raise ConflictException(f"Project {project_name} already exists")
    return None


async def init_pairing(
    addon: "KitsuAddon",
    user: "UserEntity",
    request: InitPairingRequest,
):
    await ensure_ayon_project_not_exists(
        request.project_name,
        request.project_code,
    )

    anatomy = await get_kitsu_project_anatomy(addon, request.project_id)

    await create_project_from_anatomy(
        name=request.project_name,
        code=request.project_code,
        anatomy=anatomy,
        library=False,
    )

    prj_data = {
        "kitsuProjectId": request.project_id,
    }

    await Postgres.execute(
        """UPDATE projects SET data=$1 WHERE name=$2""",
        prj_data,
        request.project_name,
    )

