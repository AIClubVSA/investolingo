# Aether Exchange backend v4

This backend-only implementation adds richer trading, economy, event chains, player progression, AI company behavior, and portfolio inspection.

Use the bundled Python runtime or Python 3.10+:

```powershell
python aether_backend_v4.py --days 10
python -m unittest -v test_aether_backend_v4.py
python aether_backend_v4.py --server --port 8000
```

Useful API calls:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/portfolio
Invoke-RestMethod http://127.0.0.1:8000/state
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/advance -ContentType 'application/json' -Body '{"days":5}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/trade -ContentType 'application/json' -Body '{"side":"buy","ticker":"IRON","qty":10}'
```

Endpoints include `/portfolio`, `/prices`, `/companies`, `/events`, `/missions`, `/state`, `/advance`, `/trade`, and `/reset`.
