# Laya Service

FastAPI service exposing Laya through the Jev-compatible `POST /v1/systemone` API.

## Run

```bash
python -m venv .venv
. .venv/bin/activate
uv sync
cp .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set `LAYA_PRELOAD=true` in production to load the Router during startup. The first run downloads the configured Hugging Face checkpoints.

Use `LAYA_DEVICE=auto` (or omit it) for automatic CPU/CUDA selection. The service translates this value to Laya's automatic device mode.

The service supports `jev-latest`, `laya`, `laya-english`, `laya-multilingual`, and `laya-typed-decisions`. It intentionally does not expose chat completions because Laya returns typed decisions rather than generated text.

## Documentation

- [API 接口文档 (Jev 兼容 System One API)](API.md)

## License

[MIT](LICENSE)

