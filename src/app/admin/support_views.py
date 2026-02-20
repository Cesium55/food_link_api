from sqladmin import BaseView, ModelView, expose

import app.support.models as support_models


class MasterChatAdmin(ModelView, model=support_models.MasterChat):
    column_list = ["user_id", "is_closed", "created_at", "updated_at"]


class MasterChatMessageAdmin(ModelView, model=support_models.MasterChatMessage):
    column_list = ["id", "user_id", "sender_type", "is_read", "created_at"]


class MasterChatSupportView(BaseView):
    name = "Master Chat Support"
    icon = "fa-solid fa-comments"

    @expose("/master-chat-support", methods=["GET"])
    async def master_chat_support_page(self, request):
        return await self.templates.TemplateResponse(
            request,
            "master_chat_support.html",
        )
