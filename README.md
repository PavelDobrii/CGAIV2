# CGAIV2

This project demonstrates a simple orchestration of a text generation model and text-to-speech service. The provided `docker-compose.yml` launches two containers: HuggingFace TGI for language generation and OpenTTS for speech synthesis. Outputs are stored under `orchestrator/outputs` so that generated text or audio files persist on the host. The tool can optionally fetch background information about a location from Wikipedia and Wikivoyage before generating text.

## Setup
1. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/).
2. Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) so Docker can access your GPU.
   This is required for running the LLM container with GPU acceleration.
3. Clone this repository:
   ```bash
   git clone <repo-url>
   cd CGAIV2
   ```
4. Start the services:
   ```bash
   docker compose up -d
   ```
   All three services will be reachable on your local machine once the images are pulled and started.
   The LLM server listens on `http://localhost:8080`, the OpenTTS server on `http://localhost:5500`, and the Kokoro server on `http://localhost:5600`.

## Docker Usage
- **Start services**: `docker compose up -d`
- **Stop services**: `docker compose down`
- Generated results are written to `orchestrator/outputs` on your machine. You can mount a different host directory by editing `docker-compose.yml`.

## Local Orchestrator
You can run the orchestration layer directly without Docker. The project
exposes both a FastAPI app and a simple command line interface.

### FastAPI
Start the API using Uvicorn:

```bash
uvicorn orchestrator.main:app
```

The server listens on `http://127.0.0.1:8000` by default. Use the `/story`
endpoint described below to generate stories. Open `http://127.0.0.1:8000/` in a
browser to use a simple HTML interface.

### CLI
The same functionality is available from the command line. Provide the prompt,
language and style as positional arguments:

```bash
python -m orchestrator.main "A brave knight" en epic --llm-url http://localhost:8080 --tts-url http://localhost:5500 --tts-engine opentts --location "Paris"
```

The `--location` option gathers background details from Wikipedia and Wikivoyage before sending the prompt to the LLM.

Each run creates a folder under `orchestrator/outputs/{slug}/` containing
`story.md` and `story.mp3`.

To use the Kokoro container instead of OpenTTS, pass `--tts-engine kokoro` and set `--tts-url http://localhost:5600` to match its address (or set `tts_engine: "kokoro"` when calling the API).
## API Endpoints
### HuggingFace TGI (LLM server)
- **URL**: `http://localhost:8080/generate`
- **Method**: `POST`
- **Example payload**:
  ```json
  {"inputs": "Hello"}
  ```
  The response contains generated text from the model specified in `MODEL_ID`.

### OpenTTS
- **URL**: `http://localhost:5500/api/tts`
- **Method**: `POST`
- **Example payload**:
  ```json
  {"text": "Hello world", "speaker": "coqui"}
  ```
  The service returns an audio file containing the spoken text.
  Available voices are defined in `services/tts_server/voices.yml`. This
  repository includes voices for Coqui TTS and Suno Bark. In addition to the
  basic `coqui` and `bark` voices, you can select gender-specific options such
  as `coqui-female-1`, `coqui-female-2`, `bark-female`, `coqui-male-1`,
  `coqui-male-2`, and `bark-male`. Choose one of these IDs by passing it as the
  `speaker` value when calling the API. The orchestrator also supports a
  separate Kokoro engine by passing `--tts-engine kokoro` (or `tts_engine: "kokoro"` in the API), which targets the `/api/kokoro` endpoint. When running this container, set `--tts-url http://localhost:5600` to match its address.

### Kokoro
- **URL**: `http://localhost:5600/api/kokoro`
- **Method**: `POST`
- **Example payload**:
  ```json
  {"text": "こんにちは"}
  ```
  Returns a spoken Japanese audio file.
#### Available Voices
The following voice IDs are defined in `services/tts_server/voices.yml`:

- `coqui`
- `bark`
- `coqui-female-1`
- `coqui-female-2`
- `bark-female`
- `coqui-male-1`
- `coqui-male-2`
- `bark-male`
- `kokoro`

Example using the `bark` voice:

```bash
curl -X POST http://localhost:5500/api/tts \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello from Bark", "speaker": "bark"}' \
     --output bark.mp3
```

### Orchestrator

- **`/story`**
  - **URL**: `http://localhost:8000/story`
  - **Method**: `POST`
  - **Example payload**:
    ```json
    {"prompt": "A brave knight", "language": "en", "style": "epic", "tts_engine": "kokoro", "location": "Paris"}
    ```
  - Runs the full workflow and saves the results to `orchestrator/outputs/{slug}/`.
    When `location` is provided, the orchestrator fetches descriptions from Wikipedia and Wikivoyage.
    The response JSON now includes the generated text and a base64-encoded copy of the audio in addition to the file paths.

  Example using the `tts_engine` parameter:

  ```bash
  curl -X POST http://localhost:8000/story \
       -H "Content-Type: application/json" \
       -d '{"prompt": "A brave knight", "language": "en", "style": "epic", "tts_engine": "kokoro"}'
  ```


### Authentication

Before generating a story you must first obtain a token using the `/login` endpoint:

```bash
curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "password"}'
```

The response JSON includes a `token` value. Pass this token in the `X-Token` header when calling `/story`:

```bash
curl -X POST http://localhost:8000/story \
     -H "Content-Type: application/json" \
     -H "X-Token: <token-from-login>" \
     -d '{"prompt": "A brave knight", "language": "en", "style": "epic"}'
```
## Example Results
A simple workflow might send a prompt to TGI and feed the returned text into a TTS engine such as OpenTTS or Kokoro. The resulting audio file will appear in `orchestrator/outputs`.
When the `/story` endpoint is used, the service responds with JSON similar to:

```json
{
  "markdown": "orchestrator/outputs/my-story/story.md",
  "audio": "orchestrator/outputs/my-story/story.mp3",
  "text": "Once upon a time...",
  "audio_base64": "<base64 data>"
}
```

## Directory Structure
- `services/llm_server` – placeholder for custom TGI configuration.
- `services/tts_server` – OpenTTS settings including `voices.yml` defining the
  available speakers.
- `orchestrator/templates` – optional templates for prompts or TTS scripts.
- `orchestrator/outputs` – location of saved outputs from all services.

## Testing
Install `pytest` and run the tests from the repository root:

```bash
pip install pytest
pytest
```

The suite spins up mocked HTTP servers to verify story and audio generation.

## License
Distributed under the MIT License. See [LICENSE](LICENSE) for details. This
project is provided for demonstration purposes and does not include any model
weights.
