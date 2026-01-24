from fastapi import Request
from fastapi.responses import RedirectResponse
from markupsafe import Markup

from logger import get_sync_logger
from utils.yookassa_client import create_yookassa_client

yookassa_client = create_yookassa_client()
logger = get_sync_logger(__name__)


def action_auto_returner(func):
    async def wrapper(self, request: Request):
        await func(self, request)
        referer = request.headers.get("Referer")
        if referer:
            return RedirectResponse(referer)
        return RedirectResponse(
            request.url_for("admin:list", identity=self.identity)
        )

    return wrapper


def action_with_ids(func):
    """Extract pks from request query params and pass as ids (list[int]) to action."""

    async def wrapper(self, request: Request):
        pks = request.query_params.get("pks")
        ids = list(map(int, pks.split(","))) if pks else []
        return await func(self, request, ids)

    return wrapper


def json_to_html(data, level=0):
    if isinstance(data, dict):
        html = '<details style="margin-left: 1.5em;"><summary>dict</summary><ul style="list-style:none; padding-left:0;">'
        for k, v in data.items():
            html += f'<li><strong>{k}:</strong> {json_to_html(v, level+1)}</li>'
        html += '</ul></details>'
        return Markup(html)
    elif isinstance(data, list):
        html = '<details><summary>list [' + str(len(data)) + ']</summary><ol>'
        for item in data:
            html += f'<li>{json_to_html(item, level+1)}</li>'
        html += '</ol></details>'
        return Markup(html)
    else:
        return str(data)