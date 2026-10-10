import json

from src.crop_service import demo_payload, required_aspects


if __name__ == "__main__":
    payload = demo_payload()
    print(json.dumps({"order": payload, "planned_aspects": required_aspects(payload["product_kind"])}, indent=2))

