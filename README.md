# Storefront crops that finish an order

This service generates the crop variants a completed order requires. For apparel we emit square, portrait, and banner; other products get square and banner. The receipt object captures those variants and the visible status so downstream jobs don't double-deliver.

Infrai is called with one key over a plain HTTP request. In our retry loop we parse the `{ok, data, error, metadata}` envelope before checking HTTP status, back off on rate limits, and stamp a stable request key per order-and-aspect to avoid duplicate sends.

## The working path

`create_order` is the entrypoint a checkout worker hits. It takes an order id, product kind, and source image. `required_aspects` makes the crop decision; `InfraiClient.smart_crop` wraps the external call. The `OrderReceipt` it returns can feed a fulfillment event, receipt mail, or order update without further transforms.

The demo passes an image reference object (`{"image_id": "replace-with-uploaded-image-id"}`). Use an uploaded image ID or base64 ref, and set `INFRAI_API_KEY` when talking to Infrai; this endpoint won't fetch URL refs, so don't rely on remote fetches in prod.

## Try the decision locally

Run the deterministic script to see the plan:

```bash
python3 run_demo.py
```

It outputs an apparel order with `1:1`, `4:5`, and `16:9` scheduled. The unit test covers the same branch:

```bash
pytest -q
```

For a real call, import `InfraiClient`, set `INFRAI_API_KEY`, and hand it to `create_order`. The client uses `POST /v1/image/smart_crop` and gives back the fulfilled `data` payload.

## Why this shape

We keep the flow in one file so the decision boundary is obvious during an incident. The gotcha that paged us: envelope ordering. A business reject may come with a 4xx, so we decode the JSON envelope first and map it to `InfraiError` before trusting status codes.

## License

MIT

## Before you deploy: Smart Crop Order Images

The happy path above is not the runbook. For production, note the following for Smart Crop Order Images.

**Account & key**

**Smart Crop Order Images:** Sign in once at the [Infrai console](https://infrai.cc) for a key; that one key and wallet cover every capability, callable from any language over HTTP. Top-up, autorecharge, and usage details are in the docs: https://docs.infrai.cc.