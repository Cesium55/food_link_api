import re
from typing import Optional
from utils.redis.client import get_redis_client
from logger import get_sync_logger

logger = get_sync_logger(__name__)


def _format_phone_number(phone: str) -> str:
    """
    Format phone number to "79..." format without spaces, dashes, etc.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        Formatted phone number starting with "7" and containing only digits
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # If number starts with 8, replace with 7
    if digits_only.startswith('8'):
        digits_only = '7' + digits_only[1:]
    
    # If number doesn't start with 7, add it
    if not digits_only.startswith('7'):
        digits_only = '7' + digits_only
    
    return digits_only


def _get_verification_code_key(phone: str) -> str:
    """Get Redis key for verification code"""
    formatted_phone = _format_phone_number(phone)
    return f"verification_code:{formatted_phone}"


async def store_verification_code(phone: str, code: str, expire_seconds: int = 300) -> None:
    """
    Store verification code in Redis
    
    Args:
        phone: Phone number
        code: Verification code
        expire_seconds: Expiration time in seconds (default: 300 = 5 minutes)
    """
    redis_client = await get_redis_client()
    key = _get_verification_code_key(phone)
    
    await redis_client.setex(key, expire_seconds, code)
    
    formatted_phone = _format_phone_number(phone)
    logger.info(
        "Verification code stored",
        extra={
            "phone": formatted_phone,
            "code": code,
            "expire_seconds": expire_seconds
        }
    )


async def get_verification_code(phone: str) -> Optional[str]:
    """
    Get verification code from Redis
    
    Args:
        phone: Phone number
        
    Returns:
        Verification code if exists, None otherwise
    """
    redis_client = await get_redis_client()
    key = _get_verification_code_key(phone)
    
    code = await redis_client.get(key)
    return code


async def delete_verification_code(phone: str) -> None:
    """
    Delete verification code from Redis
    
    Args:
        phone: Phone number
    """
    redis_client = await get_redis_client()
    key = _get_verification_code_key(phone)
    
    await redis_client.delete(key)
    
    formatted_phone = _format_phone_number(phone)
    logger.info("Verification code deleted", extra={"phone": formatted_phone})


async def verify_code(phone: str, code: str) -> bool:
    """
    Verify code and delete it if correct
    
    Args:
        phone: Phone number
        code: Verification code to check
        
    Returns:
        True if code is correct, False otherwise
    """
    stored_code = await get_verification_code(phone)
    print(stored_code)
    
    if stored_code and stored_code == code:
        await delete_verification_code(phone)
        return True
    
    return False

