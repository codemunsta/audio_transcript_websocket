import json
import uuid
import base64

from typing import Any
from pathlib import Path
from datetime import datetime

import whisper
from fastapi import WebSocket
from pydub import AudioSegment

# import faster_whisper as whisper


class WebSocketConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.audio_chunks = []
        self.audio_id = None
        self.temp_dir = Path("audio_uploads")
        self.temp_dir.mkdir(exist_ok=True)
        self.whisper_model = whisper.load_model("base")
        self.audio_mode = None

    async def connect(self):
        await self.websocket.accept()
        print("Client connected.")

    async def disconnect(self):
        print("Client disconnected.")

    def _get_input_output_paths(self, ext_in="webm", ext_out="mp3"):
        input_path = self.temp_dir / f"{self.audio_id}.{ext_in}"
        output_path = self.temp_dir / f"{self.audio_id}.{ext_out}"
        return input_path, output_path

    async def receive(self):
        data = await self.websocket.receive_text()
        return data

    async def receive_json(self) -> dict[str, Any]:
        return await self.websocket.receive_json()

    async def send(self, message: str):
        await self.websocket.send_text(message)

    async def send_json(self, data: dict):
        await self.websocket.send_json(data)

    async def respond(self, message: str):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await self.send_json({
                "event": "error",
                "payload": "Invalid JSON"
            })
            return

        event = data.get("event")
        payload = data.get("payload")

        if event == "ping":
            await self.send_json({"event": "pong", "payload": payload})

        elif event == "start_audio":
            self.audio_id = payload.get("id") or datetime.utcnow().isoformat()
            self.audio_chunks = []
            self.audio_mode = payload.get("mode", "chunk")  # e.g., 'chunk', 'blob', 'raw'
            await self.send_json({"event": "ready_for_audio"})

        elif event == "stop_audio":
            await self.finalize_audio_chunk()

        elif event == "base_64_audio":
            if not payload or "audio" not in payload or "id" not in payload:
                await self.send_json({
                    "event": "error",
                    "payload": "Missing 'audio' or 'id' in payload"
                })
                return
            await self.handle_base_64_audio(payload)

        else:
            await self.send_json({"event": "error", "payload": "Unknown event"})

    async def handle_incoming_bytes(self, data: bytes):
        if self.audio_mode == "chunk":
            await self.handle_audio_chunk(data)
        elif self.audio_mode == "blob":
            await self.handle_audio_blob_bytes(data)
        elif self.audio_mode == "raw":
            await self.handle_binary_audio(self.audio_id, data)
        else:
            await self.send_json({
                "event": "error",
                "payload": "Received binary data, but audio mode not set"
            })

    async def _save_and_transcribe(self, input_path: Path, output_format: str = "mp3"):
        output_path = input_path.with_suffix(f".{output_format}")

        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format=output_format)
        input_path.unlink(missing_ok=True)

        transcription = self.whisper_model.transcribe(str(output_path))
        text = transcription.get("text", "").strip()

        await self.send_json({
            "event": "audio_saved",
            "payload": {
                "id": self.audio_id,
                "url": f"/audio/{output_path.name}",
                "transcript": text
            }
        })

    async def handle_audio_chunk(self, chunk: bytes):
        self.audio_chunks.append(chunk)

    async def finalize_audio_chunk(self):
        self.audio_id = self.audio_id or str(uuid.uuid4())
        input_path = self.temp_dir / f"{self.audio_id}.webm"

        # Write all chunks to a raw webm file
        with open(input_path, "wb") as f:
            for chunk in self.audio_chunks:
                f.write(chunk)

        try:
            await self._save_and_transcribe(input_path)
        except Exception as e:
            await self.send_json({
                "event": "error",
                "payload": f"Failed to convert audio: {str(e)}"
            })

    async def handle_audio_blob_bytes(self, audio_bytes: bytes):
        try:
            self.audio_id = self.audio_id or str(uuid.uuid4())

            input_path = self.temp_dir / f"{self.audio_id}.webm"

            with open(input_path, "wb") as f:
                f.write(audio_bytes)

            try:
                await self._save_and_transcribe(input_path)
            except Exception as e:
                await self.send_json({
                    "event": "error",
                    "payload": f"Failed to convert audio: {str(e)}"
                })

        except Exception as e:
            await self.send_json({
                "event": "error",
                "payload": f"Failed to convert audio: {str(e)}"
            })

    async def handle_base_64_audio(self, payload: dict):
        try:
            self.audio_id = payload["id"] or str(uuid.uuid4())
            audio_base64 = payload["audio"]

            audio_bytes = base64.b64decode(audio_base64)

            input_path = self.temp_dir / f"{self.audio_id}.wav"

            with open(input_path, "wb") as f:
                f.write(audio_bytes)

            await self._save_and_transcribe(input_path)

        except Exception as e:
            await self.send_json({
                "event": "error",
                "payload": f"Failed to convert audio: {str(e)}"
            })

    async def handle_binary_audio(self, audio_id: str, audio_bytes: bytes):
        self.audio_id = audio_id or str(uuid.uuid4())
        input_path = self.temp_dir / f"{self.audio_id}.wav"

        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        try:
            await self._save_and_transcribe(input_path)
        except Exception as e:
            await self.send_json({
                "event": "error",
                "payload": f"Failed to convert audio: {str(e)}"
            })
