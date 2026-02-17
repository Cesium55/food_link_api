from app.admin.auth_views import RefreshTokenAdmin, UserAdmin
from app.admin.offers_views import (
    OfferAdmin,
    PricingStrategyAdmin,
    PricingStrategyStepAdmin,
)
from app.admin.payments_views import UserPaymentAdmin
from app.admin.product_categories_views import ProductCategoryAdmin
from app.admin.products_views import (
    ProductAdmin,
    ProductAttributeAdmin,
    ProductImageAdmin,
)
from app.admin.purchases_views import (
    PurchaseAdmin,
    PurchaseOfferAdmin,
    PurchaseOfferResultAdmin,
)
from app.admin.sellers_views import SellerAdmin, SellerImageAdmin
from app.admin.shop_points_views import ShopPointAdmin, ShopPointImageAdmin
from app.admin.support_views import MasterChatAdmin, MasterChatMessageAdmin
from app.admin.views import ReportView

__all__ = [
    "UserAdmin",
    "RefreshTokenAdmin",
    "OfferAdmin",
    "PricingStrategyAdmin",
    "PricingStrategyStepAdmin",
    "UserPaymentAdmin",
    "ProductCategoryAdmin",
    "ProductAdmin",
    "ProductImageAdmin",
    "ProductAttributeAdmin",
    "PurchaseAdmin",
    "PurchaseOfferAdmin",
    "PurchaseOfferResultAdmin",
    "SellerAdmin",
    "SellerImageAdmin",
    "ShopPointAdmin",
    "ShopPointImageAdmin",
    "MasterChatAdmin",
    "MasterChatMessageAdmin",
    "ReportView"
]
