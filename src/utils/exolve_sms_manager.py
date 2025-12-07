import re
import random
import string
import httpx
from typing import Optional
from logger import get_sync_logger
from config import settings

logger = get_sync_logger(__name__)


class ExolveSMSManager:
    """Manager for sending SMS via Exolve API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        sender_number: Optional[str] = None,
        api_url: Optional[str] = None
    ):
        """
        Initialize Exolve SMS manager
        
        Args:
            api_key: API key for authorization. If not provided, will use settings.exolve_api_key
            sender_number: Sender number or alphanumeric name. If not provided, will use settings.exolve_number
            api_url: Base URL for Exolve API. If not provided, will use settings.exolve_api_url
        """
        self.api_key = api_key or settings.exolve_api_key
        self.sender_number = sender_number or settings.exolve_number
        self.api_url = api_url or settings.exolve_api_url


        if not self.api_key:
            raise ValueError("Exolve API key must be provided")
        if not self.sender_number:
            raise ValueError("Exolve sender number must be provided")
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": self.api_key,
                # "Content-Type": "application/json"
            }
        )
    
    def _format_phone_number(self, phone: str) -> str:
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
    
    async def send_sms(self, destination: str, text: str) -> dict:
        """
        Send SMS to specified phone number with given text
        
        Args:
            destination: Recipient phone number (will be formatted automatically)
            text: Message text
            
        Returns:
            Response data from Exolve API
        """
        formatted_destination = self._format_phone_number(destination)
        
        payload = {
            "number": self.sender_number,
            "destination": formatted_destination,
            "text": text
        }
        
        try:
            logger.info(
                "Sending SMS",
                extra={
                    "destination": formatted_destination,
                    "sender": self.sender_number
                }
            )
            
            response = await self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(
                "SMS sent successfully",
                extra={
                    "destination": formatted_destination,
                    "response": data
                }
            )
            
            return data
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to send SMS: {e.response.status_code}",
                extra={
                    "destination": formatted_destination,
                    "response": e.response.text
                }
            )
            raise
        except Exception as e:
            logger.error(
                f"Error sending SMS: {str(e)}",
                extra={"destination": formatted_destination}
            )
            raise
    
    async def send_verification_code(
        self,
        destination: str,
        code_length: int = 6
    ) -> str:
        """
        Send SMS with generated verification code and return the code
        
        Args:
            destination: Recipient phone number (will be formatted automatically)
            code_length: Length of verification code (default: 6)
            
        Returns:
            Generated verification code
        """
        # Generate random numeric code
        code = ''.join(random.choices(string.digits, k=code_length))
        
        # Create message text
        text = f"Ваш код подтверждения: {code}"
        
        # Send SMS
        await self.send_sms(destination, text)
        
        logger.info(
            "Verification code SMS sent",
            extra={
                "destination": self._format_phone_number(destination),
                "code_length": code_length
            }
        )
        
        return code
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


def create_exolve_sms_manager(
    api_key: Optional[str] = None,
    sender_number: Optional[str] = None,
    api_url: Optional[str] = None
) -> ExolveSMSManager:
    """
    Create an ExolveSMSManager instance
    
    Args:
        api_key: Optional API key. If not provided, will use settings.exolve_api_key
        sender_number: Optional sender number. If not provided, will use settings.exolve_number
        api_url: Optional API URL. If not provided, will use settings.exolve_api_url
        
    Returns:
        ExolveSMSManager instance
    """
    return ExolveSMSManager(
        api_key=api_key,
        sender_number=sender_number,
        api_url=api_url
    )

