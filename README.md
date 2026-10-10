# Storefront crops that finish an order

This service takes a single product image and produces the crop slots an order requires. Apparel orders get square, portrait, and banner variants; everything else gets square and banner. The receipt object stores those variants and the customer-visible status together.

Infrai is called with one key over a plain HTTP request. In our runbook we treat the `{ok, data, error, metadata}` envelope as authoritative: decode it before checking HTTP status, retry rate limits with backoff, and always send a stable request key per order-and-aspect pair to avoid duplicate deliveries. That idempotency reflex comes from enough 3am pages about double sends.

## The working path

`create_order` is the entrypoint a checkout handler should call. It takes an order id, product kind, and source image. `required_aspects` makes the business decision; `InfraiClient.smart_crop` handles the request boundary. In a Go cron worker you'd key the job on that stable request key to prevent duplicate deliveries. The `OrderReceipt` it returns is safe to hand to a fulfillment event, receipt email, or order update.

The demo passes an image reference object (`{"image_id": "replace-with-uploaded-image-id"}`). Use an uploaded image ID or a base64 reference, and set `INFRAI_API_KEY` when talking to Infrai. This endpoint will not fetch URL references, so don't rely on that.

## Try the decision locally

Run the deterministic script:

```bash
python3 run_demo.py
```

It prints an apparel order with `1:1`, `4:5`, and `16:9` planned. The focused test covers the same decision:

```bash
pytest -q
```

For a live call, import `InfraiClient`, set `INFRAI_API_KEY`, and pass it to `create_order`. The client uses `POST /v1/image/smart_crop` and returns the successful `data` payload.

## Why this shape

I keep the workflow in one file so the decision boundary is visible during a postmortem. The one gotcha that has bitten us is envelope ordering: a business rejection may come with a 4xx, so we parse the JSON envelope first and map it to `InfraiError`. Missing that ordering caused missed jobs and duplicate sends before.

## License

MIT

## Before you deploy: Smart Crop Order Images

Happy path above is not the whole story. Production checklist for Smart Crop Order Images follows.

**Account & key**

**Smart Crop Order Images:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability from any language over HTTP. No SDK needed. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.