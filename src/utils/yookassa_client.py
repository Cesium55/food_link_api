import base64
import uuid
import httpx
from typing import Optional, Dict, Any
from logger import get_logger
from config import settings

logger = get_logger(__name__)


class YooKassaClient:
    """Client for YooKassa API v3"""

    def __init__(
        self,
        shop_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: str = "https://api.yookassa.ru/v3",
    ):
        """
        Initialize YooKassa client

        Args:
            shop_id: Shop ID from YooKassa. If not provided, will use settings.yookassa_shop_id
            secret_key: Secret key from YooKassa. If not provided, will use settings.yookassa_secret_key
            base_url: Base URL for YooKassa API
        """
        self.shop_id = shop_id or settings.yookassa_shop_id
        self.secret_key = secret_key or settings.yookassa_secret_key
        self.base_url = base_url

        if not self.shop_id or not self.secret_key:
            raise ValueError("YooKassa shop_id and secret_key must be provided")

        # Create Basic Auth header
        credentials = f"{self.shop_id}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json",
                "Idempotence-Key": "",  # Will be set per request
            },
        )

    async def create_payment(
        self,
        amount: float,
        currency: str = "RUB",
        description: Optional[str] = None,
        return_url: Optional[str] = None,
        capture: bool = True,
        idempotence_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a payment in YooKassa

        Args:
            amount: Payment amount
            currency: Payment currency (default: RUB)
            description: Payment description
            return_url: URL to redirect after payment
            capture: Automatically capture payment (default: True)
            idempotence_key: Idempotence key for request (optional, will be generated if not provided)

        Returns:
            Payment data from YooKassa API
        """
        if idempotence_key is None:
            idempotence_key = str(uuid.uuid4())

        payment_data = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": capture,
        }

        if description:
            payment_data["description"] = description

        if return_url:
            payment_data["confirmation"] = {
                "type": "redirect",
                "return_url": return_url,
            }

        headers = self.client.headers.copy()
        headers["Idempotence-Key"] = idempotence_key

        url = f"{self.base_url}/payments"

        try:
            response = await self.client.post(url, json=payment_data, headers=headers)
            response.raise_for_status()

            data = response.json()
            await logger.info(
                f"Payment created successfully",
                extra={
                    "payment_id": data.get("id"),
                    "amount": amount,
                    "currency": currency,
                },
            )

            return data
        except httpx.HTTPStatusError as e:
            await logger.error(
                f"Failed to create payment: {e.response.status_code}",
                extra={"response": e.response.text},
            )
            raise
        except Exception as e:
            await logger.error(f"Error creating payment: {str(e)}")
            raise

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Get payment information from YooKassa

        Args:
            payment_id: Payment ID from YooKassa

        Returns:
            Payment data from YooKassa API
        """
        url = f"{self.base_url}/payments/{payment_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            await logger.info(
                f"Payment retrieved successfully",
                extra={"payment_id": payment_id, "status": data.get("status")},
            )

            return data
        except httpx.HTTPStatusError as e:
            await logger.error(
                f"Failed to get payment: {e.response.status_code}",
                extra={"payment_id": payment_id, "response": e.response.text},
            )
            raise
        except Exception as e:
            await logger.error(
                f"Error getting payment: {str(e)}", extra={"payment_id": payment_id}
            )
            raise

    async def cancel_payment(
        self, payment_id: str, idempotence_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a payment in YooKassa

        Args:
            payment_id: Payment ID from YooKassa
            idempotence_key: Idempotence key for request (optional, will be generated if not provided)

        Returns:
            Canceled payment data from YooKassa API
        """
        if idempotence_key is None:
            idempotence_key = str(uuid.uuid4())

        url = f"{self.base_url}/payments/{payment_id}/cancel"

        headers = self.client.headers.copy()
        headers["Idempotence-Key"] = idempotence_key

        try:
            response = await self.client.post(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            await logger.info(
                f"Payment canceled successfully", extra={"payment_id": payment_id}
            )

            return data
        except httpx.HTTPStatusError as e:
            await logger.error(
                f"Failed to cancel payment: {e.response.status_code}",
                extra={"payment_id": payment_id, "response": e.response.text},
            )
            raise
        except Exception as e:
            await logger.error(
                f"Error canceling payment: {str(e)}", extra={"payment_id": payment_id}
            )
            raise

    async def create_refund(
        self,
        yookassa_payment_id: str,
        amount,
        currency: str = "RUB",
        reason: Optional[str] = None,
        idempotence_key: Optional[str] = None,
    ): 
        if idempotence_key is None:
            idempotence_key = str(uuid.uuid4())

        url = f"{self.base_url}/refunds"

        headers = self.client.headers.copy()
        headers["Idempotence-Key"] = idempotence_key
        refund_data = {
            "payment_id": yookassa_payment_id,
            "amount": {"value": f"{amount:.2f}", "currency": currency},
        }
        if reason:
            refund_data["description"] = reason

        # Log request
        await logger.info(
            "Sending refund request to YooKassa",
            extra={"url": url, "request_body": refund_data},
        )

        try:
            response = await self.client.post(url, json=refund_data, headers=headers)
            response.raise_for_status()

            data = response.json()
            await logger.info(
                "Refund created successfully",
                extra={"refund_id": data.get("id"), "payment_id": yookassa_payment_id, "amount": amount},
            )
            return data
        except httpx.HTTPStatusError as e:
            await logger.error(
                f"Failed to create refund: {e.response.status_code}",
                extra={"payment_id": yookassa_payment_id, "response": e.response.text},
            )
            raise
        except Exception as e:
            await logger.error(
                f"Error creating refund: {str(e)}",
                extra={"payment_id": yookassa_payment_id},
            )
            raise


    async def get_webhooks(self) -> Dict[str, Any]:
        """
        Get list of webhooks from YooKassa

        Returns:
            Webhooks data from YooKassa API
        """
        url = f"{self.base_url}/webhooks"

        # Log request details
        request_headers = dict(self.client.headers)
        # Mask Authorization header for security
        if "Authorization" in request_headers:
            auth_value = request_headers["Authorization"]
            if len(auth_value) > 20:
                request_headers["Authorization"] = f"{auth_value[:20]}...[masked]"

        await logger.info(
            "Sending GET webhooks request",
            extra={"url": url, "method": "GET", "headers": request_headers},
        )

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()
            await logger.info("Webhooks retrieved successfully")

            return data
        except httpx.HTTPStatusError as e:
            error_details = {
                "request_url": url,
                "request_method": "GET",
                "request_headers": request_headers,
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "response_headers": dict(e.response.headers),
            }
            await logger.error(
                f"Failed to get webhooks: {e.response.status_code}", extra=error_details
            )
            raise
        except Exception as e:
            await logger.error(f"Error getting webhooks: {str(e)}")
            raise

    async def create_webhook(
        self, event: str, url: str, idempotence_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a webhook subscription in YooKassa

        Args:
            event: Event type (e.g., "payment.succeeded")
            url: Webhook URL
            idempotence_key: Idempotence key for request (optional, will be generated if not provided)

        Returns:
            Created webhook data from YooKassa API
        """
        if idempotence_key is None:
            idempotence_key = str(uuid.uuid4())

        webhook_data = {"event": event, "url": url}

        headers = self.client.headers.copy()
        headers["Idempotence-Key"] = idempotence_key

        url_endpoint = f"{self.base_url}/webhooks"

        # Log request details
        request_headers = dict(headers)
        # Mask Authorization header for security
        if "Authorization" in request_headers:
            auth_value = request_headers["Authorization"]
            if len(auth_value) > 20:
                request_headers["Authorization"] = f"{auth_value[:20]}...[masked]"

        await logger.info(
            "Sending POST webhook creation request",
            extra={
                "url": url_endpoint,
                "method": "POST",
                "headers": request_headers,
                "request_body": webhook_data,
            },
        )

        try:
            response = await self.client.post(
                url_endpoint, json=webhook_data, headers=headers
            )
            response.raise_for_status()

            data = response.json()
            await logger.info(
                f"Webhook created successfully", extra={"event": event, "url": url}
            )

            return data
        except httpx.HTTPStatusError as e:
            error_details = {
                "request_url": url_endpoint,
                "request_method": "POST",
                "request_headers": request_headers,
                "request_body": webhook_data,
                "status_code": e.response.status_code,
                "response_text": e.response.text,
                "response_headers": dict(e.response.headers),
                "event": event,
                "url": url,
            }
            await logger.error(
                f"Failed to create webhook: {e.response.status_code}",
                extra=error_details,
            )
            raise
        except Exception as e:
            await logger.error(
                f"Error creating webhook: {str(e)}", extra={"event": event, "url": url}
            )
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


def create_yookassa_client(
    shop_id: Optional[str] = None, secret_key: Optional[str] = None
) -> YooKassaClient:
    """
    Create a YooKassaClient instance

    Args:
        shop_id: Optional shop ID. If not provided, will use settings.yookassa_shop_id
        secret_key: Optional secret key. If not provided, will use settings.yookassa_secret_key

    Returns:
        YooKassaClient instance
    """
    return YooKassaClient(shop_id=shop_id, secret_key=secret_key)
