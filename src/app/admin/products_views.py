from sqladmin import ModelView

import app.products.models as products_models


class ProductAdmin(ModelView, model=products_models.Product):
    pass


class ProductImageAdmin(ModelView, model=products_models.ProductImage):
    pass


class ProductAttributeAdmin(ModelView, model=products_models.ProductAttribute):
    pass
