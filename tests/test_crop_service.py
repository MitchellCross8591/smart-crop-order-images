import json

from src.crop_service import InfraiClient, demo_payload, required_aspects


def test_apparel_gets_square_portrait_and_banner_slots():
    assert required_aspects("apparel") == ("1:1", "4:5", "16:9")
    assert required_aspects("book") == ("1:1", "16:9")


def test_smart_crop_sends_image_reference_object():
    def opener(request, timeout):
        assert json.loads(request.data) == {"image": demo_payload()["image"], "aspect": "1:1"}
        class Response:
            status = 200

            def read(self):
                return b'{"ok": true, "data": {"image": "cropped"}}'

        return Response()

    assert InfraiClient(api_key="test", opener=opener).smart_crop(demo_payload()["image"], "1:1") == {"image": "cropped"}
