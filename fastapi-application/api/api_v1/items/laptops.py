from typing import Annotated, Sequence
import logging
from uuid import UUID

from api.api_v1.items.filters.laptop_filter import (
    LaptopFilterParams,
    filter_laptops,
    get_laptops_attrs,
)
from common_logger.logger_config import configure_logger
from api.api_v1.check_perms_loggin import check_if_item_belongs
from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
    Path,
    HTTPException,
)
from api.dependencies.authentication.fastapi_users_ import (
    current_superuser,
    current_active_user,
    current_verified_user,
)
from core.config import settings
from core.models import User, db_helper
from core.models.items import Laptop
from core.redis_helper import redis
from core.schemas.items import (
    LaptopFullModel,
    LaptopCreate,
    LaptopPreviewModelWithID,
    LaptopUpdatePartial,
)
from sqlalchemy.ext.asyncio import AsyncSession
from crud.items_crud.laptops import crud_laptop
import orjson

logger = logging.getLogger(__name__)

user_state = current_verified_user


configure_logger(level=logging.INFO)
router = APIRouter(
    prefix=settings.api.v1.laptops,
    tags=["Laptops"],
)


@router.get(
    "/get-unique-attrs",
)
async def get_unique_laptop_attr(
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ]
):
    cached_data = await redis.get("laptops_attrs")
    if cached_data:
        return orjson.loads(cached_data)
    result = await get_laptops_attrs(
        session=session,
    )
    await redis.set(
        "laptops_attrs",
        orjson.dumps(result),
        ex=settings.redis.redis_expire,
    )
    return result


@router.post(
    "/create-laptop",
    response_model=LaptopCreate,
    status_code=status.HTTP_201_CREATED,
)
async def create_laptop(
    user: Annotated[
        User,
        Depends(user_state),
    ],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
    model_in: LaptopCreate,
) -> "Laptop":
    new_laptop: "Laptop" = await crud_laptop.create(
        session,
        user_id=user.id,
        data=model_in.model_dump(),
    )
    return new_laptop


@router.get(
    "/get-laptops-filtered/",
    response_model=list[LaptopPreviewModelWithID],
)
async def get_laptops_filtered(
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
    filters: LaptopFilterParams = Depends(),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Sequence[Laptop]:
    result: Sequence[Laptop] = await filter_laptops(
        session=session,
        filters=filters,
        offset=offset,
        limit=limit,
    )
    return result


@router.get(
    "/get-laptop-by-uuid/{uuid}",
    response_model=LaptopFullModel,
)
async def get_laptop_by_uuid(
    uuid: Annotated[UUID, Path],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
) -> Laptop | None:
    laptop: "Laptop" = await crud_laptop.get_by_uuid(
        session=session,
        item_uuid=uuid,
    )
    if laptop is not None:
        return laptop
    raise HTTPException(
        status_code=404,
        detail=f"Laptop {uuid} not found",
    )


@router.get(
    "/get-laptops-preview/",
    response_model=list[LaptopPreviewModelWithID],
)
async def get_laptops_preview(
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Sequence["Laptop"]:
    laptops: Sequence["Laptop"] = await crud_laptop.get_all(
        session=session,
        offset=offset,
        limit=limit,
    )
    return laptops


@router.get(
    "/get-my-laptops",
    response_model=list[LaptopPreviewModelWithID],
)
async def get_my_laptops(
    user: Annotated[
        User,
        Depends(user_state),
    ],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
) -> Sequence["Laptop"]:
    laptops: Sequence["Laptop"] = await crud_laptop.get_users(
        session=session,
        user_id=user.id,
    )
    return laptops


@router.get(
    "/get-laptops-detail",
    response_model=list[LaptopFullModel],
)
async def get_laptops_detail(
    user: Annotated[
        User,
        Depends(current_superuser),
    ],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Sequence["Laptop"]:
    """
    Dumps all full laptops models from DB in JSON array
    available to superusers only
    :param user:
    :param session:
    :param offset:
    :param limit:
    :return:
    """
    laptops: Sequence["Laptop"] = await crud_laptop.get_all(
        session=session,
        offset=offset,
        limit=limit,
    )
    return laptops


@router.patch(
    "/patch-laptop/{uuid}",
    response_model=LaptopUpdatePartial,
)
async def update_laptop_partial(
    uuid: Annotated[
        UUID,
        Path,
    ],
    laptop_update: LaptopUpdatePartial,
    user: Annotated[
        User,
        Depends(user_state),
    ],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
) -> Laptop:
    laptop: Laptop = await crud_laptop.get_by_uuid(
        session=session,
        item_uuid=uuid,
    )
    check_if_item_belongs(
        user=user,
        model=laptop,
        message="updated",
    )
    result: Laptop = await crud_laptop.update(
        session=session,
        model_update=laptop_update,
        model_instance=laptop,
        partial=True,
    )
    return result


@router.delete(
    "/delete-laptop/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_laptop(
    uuid: Annotated[
        UUID,
        Path,
    ],
    user: Annotated[
        User,
        Depends(user_state),
    ],
    session: Annotated[
        AsyncSession,
        Depends(db_helper.session_getter),
    ],
) -> None:
    laptop: Laptop = await crud_laptop.get_by_uuid(
        session=session,
        item_uuid=uuid,
    )
    check_if_item_belongs(
        user=user,
        model=laptop,
        message="deleted",
    )
    await crud_laptop.delete(
        session=session,
        model_instance=laptop,
    )
