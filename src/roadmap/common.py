import base64
import json
import logging
import typing as t
import urllib.parse
import urllib.request

from datetime import date
from urllib.error import HTTPError

from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from roadmap.config import Settings
from roadmap.database import get_db
from roadmap.models import LifecycleType


logger = logging.getLogger("uvicorn.error")


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/v1/ping") == -1


async def decode_header(
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> str:
    # https://github.com/RedHatInsights/identity-schemas/blob/main/3scale/identities/basic.json
    if x_rh_identity is None:
        return ""

    decoded_id_header = base64.b64decode(x_rh_identity).decode("utf-8")
    id_header = json.loads(decoded_id_header)
    identity = id_header.get("identity", {})
    org_id = identity.get("org_id", "")

    return org_id


async def query_rbac(
    settings: t.Annotated[Settings, Depends(Settings.create)],
    x_rh_identity: t.Annotated[str | None, Header(include_in_schema=False)] = None,
) -> list[dict[t.Any, t.Any]]:
    if settings.dev:
        return [
            {
                "permission": "inventory:*:*",
                "resourceDefinitions": [],
            }
        ]

    params = {
        "application": "inventory",
        "limit": 1000,
    }

    headers = {"X-RH-Identity": x_rh_identity} if x_rh_identity else {}
    if not settings.rbac_url:
        return [{}]

    req = urllib.request.Request(
        f"{settings.rbac_url}/api/rbac/v1/access/?{urllib.parse.urlencode(params, doseq=True)}",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.load(response)
    except HTTPError as err:
        logger.error(f"Problem querying RBAC: {err}")
        raise HTTPException(status_code=err.code, detail=err.msg)

    return data.get("data", [{}])


async def check_inventory_access(
    permissions: t.Annotated[list[dict[t.Any, t.Any]], Depends(query_rbac)],
) -> list[str]:
    """Check the given permissions for inventory access.

    Return a boolean as well as any detailed access definitions.
    """
    inventory_access_perms = {"inventory:*:*", "inventory:hosts:read"}

    has_access = False
    resource_definitions = []
    for permission in permissions:
        if perm := permission.get("resourceDefinitions"):
            resource_definitions.append(*perm)
        else:
            if permission.get("permission") in inventory_access_perms:
                has_access = True

    if not has_access:
        raise HTTPException(status_code=403, detail="Not authorized to access host inventory")

    return resource_definitions


# FIXME: This should be cached
async def query_host_inventory(
    org_id: t.Annotated[str, Depends(decode_header)],
    session: t.Annotated[AsyncSession, Depends(get_db)],
    settings: t.Annotated[Settings, Depends(Settings.create)],
    groups: t.Annotated[list[str], Depends(check_inventory_access)],
    major: int | None = None,
    minor: int | None = None,
):
    if settings.dev:
        org_id = "1234"

    if groups:
        # TODO: Implement group filtering
        raise HTTPException(501, detail="Group filtering is not yet implemented")

    query = "SELECT * FROM hbi.hosts WHERE org_id = :org_id"
    if major is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,major}}' = :major"

    if minor is not None:
        query = f"{query} AND system_profile_facts #>> '{{operating_system,minor}}' = :minor"

    result = await session.stream(
        text(query),
        params={
            "org_id": org_id,
            "major": str(major),
            "minor": str(minor),
        },
    )
    yield result


def get_lifecycle_type(products: list[dict[str, str]]) -> LifecycleType:
    """Calculate lifecycle type based on the product ID.

    https://downloads.corp.redhat.com/internal/products
    https://github.com/RedHatInsights/rhsm-subscriptions/tree/main/swatch-product-configuration/src/main/resources/subscription_configs/RHEL

    Mainline < EUS < E4S/EEUS

    EUS --> 70, 73, 75
    ELS --> 204
    E4S/EEUS --> 241

    """
    ids = {item.get("id") for item in products}
    type = LifecycleType.mainline

    if any(id in ids for id in {"70", "73", "75"}):
        type = LifecycleType.eus

    if "204" in ids:
        type = LifecycleType.els

    if "241" in ids:
        type = LifecycleType.e4s

    return type


def sort_attrs(attr, /, *attrs) -> t.Callable:
    def _getter(item):
        # If an attribute is None, use a 0 instead of None for the purpose of sorting
        # FIXME: There is a bug if getatter() is an empty string "", a 0 is used instead of an empty string.
        return tuple(getattr(item, a) or 0 for a in (attr, *attrs))

    return _getter


def ensure_date(value: str | date):
    """Ensure the date value is a date object."""
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Date must be in ISO 8601 format")
