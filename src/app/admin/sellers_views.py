from sqladmin import ModelView

import app.sellers.models as sellers_models


class SellerAdmin(ModelView, model=sellers_models.Seller):
    column_list = ["id", "full_name", ]


class SellerImageAdmin(ModelView, model=sellers_models.SellerImage):
    pass
