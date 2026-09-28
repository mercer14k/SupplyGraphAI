# Reproduce the screenshots

Start the API on 8041 and frontend on 5197 using README. Then:

```sh
cd apps/web
pnpm exec playwright install chromium
pnpm test:e2e
```

The first test captures `network-overview.png` and `global-network.png` at 1440×1080 (full-page output). The mobile test captures `mobile.png` at 390×844. Native systems with installed Chrome can use `E2E_CHANNEL=chrome pnpm test:e2e`. For Compose set `E2E_BASE_URL=http://127.0.0.1:8080`.

Screenshots show real API outputs for seed 42 / September 15 snapshot, default PORT-0001 fourteen-day outage. Values are synthetic planning results, not live risk indicators. Screenshot capture is part of the test and should be regenerated after UI or data changes.
