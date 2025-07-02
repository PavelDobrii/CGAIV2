# CGAIV2

This project demonstrates a simple orchestration of a text generation model and text-to-speech service. The provided `docker-compose.yml` launches two containers: HuggingFace TGI for language generation and OpenTTS for speech synthesis. Outputs are stored under `orchestrator/outputs` so that generated text or audio files persist on the host.

## Setup
1. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/).
2. Clone this repository:
   ```bash
   git clone <repo-url>
   cd CGAIV2
   ```
3. Start the services:
   ```bash
   docker compose up -d
   ```
   Both services will be reachable on your local machine once the images are pulled and started.

## Docker Usage
- **Start services**: `docker compose up -d`
- **Stop services**: `docker compose down`
- Generated results are written to `orchestrator/outputs` on your machine. You can mount a different host directory by editing `docker-compose.yml`.

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
  {"text": "Hello world", "speaker": "en"}
  ```
  The service returns an audio file containing the spoken text.

## Example Results
A simple workflow might send a prompt to TGI and feed the returned text into OpenTTS. The resulting audio file will appear in `orchestrator/outputs`.

## Directory Structure
- `services/llm_server` – placeholder for custom TGI configuration.
- `services/tts_server` – placeholder for custom OpenTTS configuration.
- `orchestrator/templates` – optional templates for prompts or TTS scripts.
- `orchestrator/outputs` – location of saved outputs from both services.

## License
This project is distributed for demonstration purposes and does not include any model weights.
