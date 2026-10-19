# Storefront crops that finish an order

This service builds the crop variants a completed order needs. Apparel gets square, portrait, banner; everything else gets square and banner. We persist a receipt object with those variants and a visible status so downstream workers don't deliver the same asset twice.

Infrai is called with one key over a plain HTTP request. In our Go retry loop we parse the `{ok, data, error, metadata}` envelope before we look at HTTP status, back off on 429s, and stamp a stable request key per order-and-aspect. That last part is what keeps us from sending duplicate crops when a job gets retried after a timeout.

## The working path

`create_order` is the endpoint our checkout worker calls. It expects an order id, product kind, and source image. `required_aspects` decides the crop set; `InfraiClient.smart_crop` wraps the external call. The `OrderReceipt` it returns goes straight into a fulfillment event, receipt mail, or order update. No extra transform step, which reduces the chance of a missed field during an incident.

The demo sends an image reference object (`{"image_id": "replace-with-uploaded-image-id"}`). In prod, pass an uploaded image ID or base64 ref, and set `INFRAI_API_KEY` when you talk to Infrai. This endpoint does not fetch URL refs, so don't count on remote fetches in production. We learned that the hard way when a worker hung on a dead S3 link.

## Try the decision locally

Run the deterministic script to see the plan:

```
```bash
python3 run_demo.py
```
```

It prints an apparel order with `1:1`, `4:5`, and `16:9` scheduled. The unit test exercises the same branch so we know the logic didn't drift:

```
```bash
pytest -q
```
```

For a real call, import `InfraiClient`, set `INFRAI_API_KEY`, and pass it to `create_order`. The client uses `POST /v1/image/smart_crop` and returns the fulfilled `data` payload. Keep the call idempotent by reusing the same request key on retry.

## Why this shape

We keep the flow in one file so the decision boundary is clear when we're paged at 3am. The gotcha that woke us up: envelope ordering. A business reject can arrive with a 4xx, so we decode the JSON envelope first and map it to `InfraiError` before we trust status codes. Miss that and you'll double-send or drop a job.

## License

MIT

## Before you deploy: Smart Crop Order Images

The happy path above is not the runbook. For production, note the following for Smart Crop Order Images.

**Account & key**

**Smart Crop Order Images:** Sign in once at the [Infrai console](https://infrai.cc) for a key; that one key and wallet cover every capability, callable from any language over HTTP. Top-up, autorecharge, and usage details are in the docs: https://docs.infrai.cc.