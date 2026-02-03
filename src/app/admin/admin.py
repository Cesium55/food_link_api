from sqladmin import Admin
from fastapi.templating import Jinja2Templates
from fastapi import Request, Response
from sqladmin.authentication import login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
from datetime import datetime, timezone, timedelta

from app.purchases.manager import PurchasesManager
from app.purchases.models import Purchase, PurchaseOffer
from app.offers.models import Offer
from app.shop_points.models import ShopPoint
from app.sellers.manager import SellersManager
from app.sellers.models import Seller
from database import get_async_session
from logger import get_logger
from config import settings


logger = get_logger("admin")

class MyAdmin(Admin):

    purchase_manager: PurchasesManager

    def __init__(
        self,
        app,
        engine=None,
        session_maker=None,
        base_url="/admin",
        title="Admin",
        logo_url=None,
        favicon_url=None,
        middlewares=None,
        debug=False,
        templates_dir="templates",
        authentication_backend=None,
        ########################
        purchase_manager=PurchasesManager(),
    ):
        super().__init__(
            app,
            engine,
            session_maker,
            base_url,
            title,
            logo_url,
            favicon_url,
            middlewares,
            debug,
            templates_dir,
            authentication_backend,
        )
        self.purchase_manager = purchase_manager
        self.sellers_manager = SellersManager()

    @login_required
    async def index(self, request: Request) -> Response:
        """Index route which can be overridden to create dashboards."""
        context = {}
        async with get_async_session() as session:
            one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Single optimized query with all needed relations
            result = await session.execute(
                select(Purchase)
                .where(Purchase.created_at >= one_month_ago)
                .options(
                    selectinload(Purchase.purchase_offers).selectinload(PurchaseOffer.offer)
                    .selectinload(Offer.shop_point)
                    .selectinload(ShopPoint.seller)
                    .selectinload(Seller.images)
                )
                .order_by(Purchase.created_at.desc())
            )
            purchases = result.scalars().all()
            
            # Process data efficiently - only what's needed
            unique_seller_ids = set()
            last_month_purchases = []
            
            for purchase in purchases:
                # Minimal purchase data
                purchase_dict = {
                    "status": purchase.status,
                    "total_cost": float(purchase.total_cost) if purchase.total_cost else 0.0,
                    "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
                    "purchase_offers": []
                }
                
                # Process purchase offers
                sellers_in_purchase = set()
                for po in purchase.purchase_offers:
                    if po.offer and po.offer.shop_point and po.offer.shop_point.seller:
                        seller = po.offer.shop_point.seller
                        seller_id = seller.id
                        unique_seller_ids.add(seller_id)
                        
                        # Track sellers for count (once per purchase)
                        if seller_id not in sellers_in_purchase:
                            sellers_in_purchase.add(seller_id)
                        
                        # Add all offers for money calculation
                        purchase_dict["purchase_offers"].append({
                            "quantity": po.quantity,
                            "cost_at_purchase": float(po.cost_at_purchase) if po.cost_at_purchase else 0.0,
                            "seller_id": seller_id,
                            "seller_name": seller.short_name or seller.full_name,
                        })
                
                last_month_purchases.append(purchase_dict)
            
            # Get seller image data in one batch (bucket and path only)
            seller_image_data = {}
            if unique_seller_ids:
                sellers_result = await session.execute(
                    select(Seller)
                    .where(Seller.id.in_(list(unique_seller_ids)))
                    .options(selectinload(Seller.images))
                )
                sellers = sellers_result.scalars().all()
                
                bucket_name = settings.s3_bucket_name
                
                for seller in sellers:
                    if seller.images and len(seller.images) > 0:
                        # Normalize path - remove s3://bucket/ prefix if present
                        image_path = seller.images[0].path
                        
                        if image_path.startswith('s3://'):
                            # Remove s3:// prefix and bucket name
                            parts = image_path.replace('s3://', '').split('/', 1)
                            if len(parts) > 1:
                                image_path = parts[1]  # Take path after bucket name
                            else:
                                image_path = parts[0]
                        
                        # Store bucket and path separately
                        seller_image_data[seller.id] = {
                            "bucket": bucket_name,
                            "path": image_path
                        }
                    else:
                        seller_image_data[seller.id] = None
            
            # Serialize to JSON for template
            context["last_month_purchases"] = json.dumps(last_month_purchases)
            context["seller_image_data"] = json.dumps(seller_image_data)
        return await self.templates.TemplateResponse(request, "sqladmin/index.html", context)
