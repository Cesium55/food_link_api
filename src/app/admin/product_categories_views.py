from sqladmin import ModelView

import app.product_categories.models as product_categories_models


class ProductCategoryAdmin(
    ModelView, model=product_categories_models.ProductCategory
):
    pass
