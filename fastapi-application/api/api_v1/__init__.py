from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from core.config import settings

from .users import router as users_router

from .auth import router as auth_router

from .users import router as users_router

from .messages import router as messages_router

from .items.laptops import router as laptops_router

from .items.monitors import router as monitors_router

from .items.desktops import router as desktops_router

http_bearer = HTTPBearer(auto_error=False)
router = APIRouter(
    prefix=settings.api.v1.prefix,
    dependencies=[Depends(http_bearer)],
)
# router.include_router(
#     users_router,
#     prefix=settings.api.v1.users,
# )
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(messages_router)

router.include_router(laptops_router)
router.include_router(monitors_router)
router.include_router(desktops_router)
