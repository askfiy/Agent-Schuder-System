import fastapi

from core.features.tasks.router import controller as tasks_controller
from core.features.tasks_unit.router import controller as units_controller
from core.features.tasks_chat.router import controller as chats_controller
from core.features.tasks_audit.router import controller as audits_controller
from core.features.tasks_history.router import controller as histories_controller
from core.features.tasks_workspace.router import controller as workspaces_controller

api_router = fastapi.APIRouter()

api_router.include_router(tasks_controller)
api_router.include_router(units_controller)
api_router.include_router(chats_controller)
api_router.include_router(audits_controller)
api_router.include_router(histories_controller)
api_router.include_router(workspaces_controller)
