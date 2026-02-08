import httpx
from typing import Any, Optional, Dict, Union
from datetime import datetime
from config import settings
import random


class TelegramGatewayError(Exception):
    """Исключения от Gateway API"""

    pass


class TelegramGatewayClient:
    """
    Асинхронный клиент для Telegram Gateway API (отправка кодов верификации)

    Документация: https://core.telegram.org/gateway/api

    Пример:
        async with TelegramGatewayClient(access_token="your_gateway_token") as client:
            status = await client.send_verification_message(
                phone_number="+1234567890",
                code_length=5,
                callback_url="https://your-site.com/callback"
            )
    """

    BASE_URL = "https://gatewayapi.telegram.org/"

    def __init__(
        self,
        access_token: str = settings.tg_gateway_access_token,
        timeout: float = 30.0,
        proxy: Optional[str] = None,
    ):
        self.access_token = access_token
        self.client: Optional[httpx.AsyncClient] = None

        self.timeout = httpx.Timeout(timeout)
        self.proxy = proxy

    async def __aenter__(self) -> "TelegramGatewayClient":
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "TelegramGatewayClient/1.0 (httpx)",
        }

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=self.timeout,
            http2=True,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Any:
        if self.client is None:
            raise RuntimeError(
                "Клиент не инициализирован. Используйте через async with"
            )

        try:
            response = await self.client.request(
                method=method.upper(), url=endpoint, params=params, json=json, **kwargs
            )

            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            if not data.get("ok"):
                error_msg = data.get("error", "Unknown error")
                raise TelegramGatewayError(f"Gateway error: {error_msg}")

            return data.get("result")

        except httpx.HTTPStatusError as e:
            try:
                err_data = e.response.json()
                msg = err_data.get("error", str(e))
            except Exception:
                msg = str(e)
            raise TelegramGatewayError(msg) from e

        except httpx.RequestError as e:
            raise TelegramGatewayError(f"Ошибка соединения: {e}") from e

    # ─────────────── Основные методы Gateway API ───────────────
    async def send_verification_code(
        self,
        phone_number: str,
    )-> str:
        code = random.randint(100000, 999999)
        await self.send_verification_message(
            phone_number=phone_number,
            code=code
        )
        return str(code)

    async def send_verification_message(
        self,
        phone_number: str,
        code: Optional[str] = None,  # свой код (4–8 цифр)
        code_length: Optional[int] = 6,  # 4–8, если code не передан
        ttl: Optional[int] = None,  # 30–3600 сек
        callback_url: Optional[str] = None,
        payload: Optional[str] = None,  # до 128 байт
        request_id: Optional[
            str
        ] = None,  # для бесплатной отправки после checkSendAbility
    ) -> Dict:
        """
        Отправляет сообщение с кодом верификации.
        Возвращает RequestStatus.
        """
        payload_data = {
            "phone_number": phone_number.lstrip("+"),  # API принимает без +
        }

        if code:
            payload_data["code"] = code
        if code_length:
            payload_data["code_length"] = code_length
        if ttl:
            payload_data["ttl"] = ttl
        if callback_url:
            payload_data["callback_url"] = callback_url
        if payload:
            payload_data["payload"] = payload
        if request_id:
            payload_data["request_id"] = request_id

        return await self._request("POST", "sendVerificationMessage", json=payload_data)

    async def check_send_ability(
        self,
        phone_number: str,
    ) -> Dict:
        """
        Проверяет возможность отправки верификационного сообщения.
        Возвращает RequestStatus с request_id (если возможно).
        """
        params = {"phone_number": phone_number.lstrip("+")}
        return await self._request("GET", "checkSendAbility", params=params)

    async def check_verification_status(
        self,
        request_id: str,
    ) -> Dict:
        """
        Проверяет статус отправленного запроса (доставка + верификация кода).
        """
        params = {"request_id": request_id}
        return await self._request("GET", "checkVerificationStatus", params=params)

    async def revoke_verification_message(
        self,
        request_id: str,
    ) -> bool:
        """
        Пытается отозвать сообщение.
        Возвращает True, если запрос принят (но не гарантирует удаление).
        """
        params = {"request_id": request_id}
        result = await self._request("POST", "revokeVerificationMessage", json=params)
        return bool(result)


# ─── Пример использования ───
if __name__ == "__main__":
    import asyncio

    async def main():
        # Замени на свой реальный токен из https://gateway.telegram.org/account/api
        TOKEN = "gw_abc123def456..."

        async with TelegramGatewayClient(access_token=TOKEN) as gw:
            try:
                # 1. Проверяем возможность отправки (бесплатно)
                ability = await gw.check_send_ability(phone_number="+79991234567")
                print("Можно отправить?", ability)

                # 2. Отправляем код
                status = await gw.send_verification_message(
                    phone_number="+79991234567",
                    code_length=5,
                    callback_url="https://example.com/webhook",
                )
                print("Отправлено → request_id:", status.get("request_id"))

                # 3. Проверяем статус позже
                # await asyncio.sleep(10)
                # upd = await gw.check_verification_status(status["request_id"])
                # print(upd)

            except TelegramGatewayError as e:
                print("Ошибка Gateway API:", e)

    asyncio.run(main())
