from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import json
from app.debug.init import initialize_categories_from_json_file
from app.purchases.tasks import cancel_all_expired_purchases

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/init-categories-from-file")
async def initialize_categories_from_file(request: Request) -> Dict[str, Any]:
    """
    Initialize product categories from categories.md file.
    This will read the JSON structure from categories.md and create/update categories.
    """
    try:
        result = await initialize_categories_from_json_file(request.state.session)
        
        return {
            "success": True,
            "message": "Categories initialized from file successfully",
            "result": result,
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON in categories file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize categories from file: {str(e)}"
        )


@router.post("/cancel-expired-purchases")
async def cancel_expired_purchases(request: Request) -> Dict[str, Any]:
    """
    Cancel all expired purchases with pending status.
    This endpoint manually checks and cancels all expired purchases without using Celery.
    Useful for debugging and manual cleanup.
    """
    try:
        result = await cancel_all_expired_purchases()
        
        return {
            "success": True,
            "message": f"Cancelled {result['cancelled_count']} expired purchases",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel expired purchases: {str(e)}"
        )
