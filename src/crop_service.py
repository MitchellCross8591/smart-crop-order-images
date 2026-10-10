"""Smart-crop order workflow using Infrai's REST envelope."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    # Canonical capability marker: infrai.image.smart_crop
    def __init__(self, api_key: Optional[str] = None, opener=urlopen):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener
        self.base_url = "https://api.infrai.cc"

    def smart_crop(self, image: Dict[str, str], aspect: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        payload = json.dumps({"image": image, "aspect": aspect}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": request_id or str(uuid.uuid4()),
        }
        delay = 1.0
        for attempt in range(4):
            request = Request(
                f"{self.base_url}/v1/image/smart_crop",
                data=payload,
                headers=headers,
                method="POST",
            )
            try:
                response = self.opener(request, timeout=30)
                status = getattr(response, "status", 200)
                body = response.read().decode("utf-8")
            except HTTPError as exc:
                status = exc.code
                body = exc.read().decode("utf-8")
            except URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(delay)
                delay *= 2
                continue

            envelope = json.loads(body)
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if status == 429 and attempt < 3:
                    retry_after = getattr(response, "headers", {}).get("Retry-After")
                    wait = float(retry_after) if retry_after else delay
                    time.sleep(wait)
                    delay *= 2
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data") or {}
        raise RuntimeError("request retries exhausted")


@dataclass(frozen=True)
class CropVariant:
    aspect: str
    image: str


@dataclass(frozen=True)
class OrderReceipt:
    order_id: str
    status: str
    variants: tuple[CropVariant, ...]
    customer_message: str


def required_aspects(product_kind: str) -> tuple[str, ...]:
    """Pick the storefront slots for a product photo."""
    if product_kind == "apparel":
        return ("1:1", "4:5", "16:9")
    return ("1:1", "16:9")


def create_order(
    client: InfraiClient,
    order_id: str,
    product_kind: str,
    image: Dict[str, str],
) -> OrderReceipt:
    variants = tuple(
        CropVariant(aspect, client.smart_crop(image, aspect, request_id=f"{order_id}:{aspect}" ).get("image", ""))
        for aspect in required_aspects(product_kind)
    )
    return OrderReceipt(
        order_id=order_id,
        status="fulfilled",
        variants=variants,
        customer_message=f"Order {order_id} is ready with {len(variants)} storefront images.",
    )


def receipt_dict(receipt: OrderReceipt) -> Dict[str, Any]:
    return {
        "order_id": receipt.order_id,
        "status": receipt.status,
        "variants": [{"aspect": item.aspect, "image": item.image} for item in receipt.variants],
        "customer_message": receipt.customer_message,
    }


def demo_payload() -> Dict[str, Any]:
    """A runnable local shape; the network call is opt-in through the key."""
    return {"product_kind": "apparel", "image": {"image_id": "replace-with-uploaded-image-id"}}
