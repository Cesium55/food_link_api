"""
Unit-test bootstrap for SQLAlchemy model registry.

These imports ensure that all ORM models are registered in Base metadata
before tests trigger mapper configuration via relationship()/selectinload().
"""

from app.auth import models as _auth_models  # noqa: F401
from app.offers import models as _offers_models  # noqa: F401
from app.payments import models as _payments_models  # noqa: F401
from app.product_categories import models as _product_categories_models  # noqa: F401
from app.products import models as _products_models  # noqa: F401
from app.purchases import models as _purchases_models  # noqa: F401
from app.sellers import models as _sellers_models  # noqa: F401
from app.shop_points import models as _shop_points_models  # noqa: F401
from app.support import models as _support_models  # noqa: F401
