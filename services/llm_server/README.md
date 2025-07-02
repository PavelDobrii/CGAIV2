# LLM Server

This directory documents how to run the HuggingFace Text Generation Inference container used in `docker-compose.yml`.

## Model Weights
The compose file sets the environment variable `MODEL_ID=deepseek-ai/deepseek-r1-distill-qwen-14b`. When the container starts, it will download this model from HuggingFace. To reuse weights across container restarts or provide your own copy of the model, mount a host directory and set `HF_HOME` accordingly:

```yaml
services:
  llm:
    volumes:
      - /path/to/hf_cache:/data
    environment:
      - HF_HOME=/data
```

If the model requires authentication, supply `HUGGING_FACE_HUB_TOKEN` in the environment.

## GPU Access
GPU usage is configured via `docker-compose.yml` using `deploy.resources.reservations.devices` so Docker will allocate available GPUs when the container runs.
