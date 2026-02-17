from sqladmin import ModelView

import app.support.models as support_models


class MasterChatAdmin(ModelView, model=support_models.MasterChat):
    column_list = ["user_id", "is_closed", "created_at", "updated_at"]


class MasterChatMessageAdmin(ModelView, model=support_models.MasterChatMessage):
    column_list = ["id", "user_id", "sender_type", "is_read", "created_at"]
