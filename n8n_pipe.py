"""
title: n8n Pipe Function
author: Cole Medin
contributors: Ricardo Leon (leoric-crown)
author_url: https://www.youtube.com/@ColeMedin
version: 0.3.2

This module defines a Pipe class that utilizes N8N for an Agent with support for sending image attachments to n8n
No support for receiving image attachments from n8n.
Metadata: original filename is not preserved, mime and size are sent to n8n.
"""

from typing import Optional, Callable, Awaitable
from pydantic import BaseModel, Field
import time
import requests
import base64
import io
import json

# Mapping of MIME types to file extensions
MIME_TO_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "webp": "webp",
    "gif": "gif",
}


def extract_event_info(event_emitter) -> tuple[Optional[str], Optional[str]]:
    if not event_emitter or not event_emitter.__closure__:
        return None, None
    for cell in event_emitter.__closure__:
        if isinstance(request_info := cell.cell_contents, dict):
            chat_id = request_info.get("chat_id")
            message_id = request_info.get("message_id")
            return chat_id, message_id
    return None, None


class Pipe:
    class Valves(BaseModel):
        n8n_url: str = Field(
            default="https://n8n.[your domain].com/webhook/[your webhook URL]"
        )
        n8n_bearer_token: str = Field(default="...")
        input_field: str = Field(default="chatInput")
        response_field: str = Field(default="output")
        emit_interval: float = Field(
            default=2.0, description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "n8n_pipe"
        self.name = "N8N Pipe"
        self.valves = self.Valves()
        self.last_emit_time = 0
        pass

    async def emit_status(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        level: str,
        message: str,
        done: bool,
    ):
        current_time = time.time()
        if (
            __event_emitter__
            and self.valves.enable_status_indicator
            and (
                current_time - self.last_emit_time >= self.valves.emit_interval or done
            )
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> Optional[dict]:

        await self.emit_status(
            __event_emitter__, "info", "/Calling N8N Workflow...", False
        )
        chat_id, _ = extract_event_info(__event_emitter__)
        messages = body.get("messages", [])

        # Verify a message is available
        if messages:
            # Get the most recent user message by iterating in reverse
            user_message = None
            for msg in reversed(messages):
                if msg["role"] == "user":
                    user_message = msg
                    break

            if user_message and isinstance(user_message["content"], list):
                # Extract text content and file attachments
                question = ""
                processed_attachments = []

                for content_item in user_message["content"]:
                    if content_item["type"] == "text":
                        question = content_item["text"]
                    elif (
                        content_item["type"] == "image_url"
                        and "url" in content_item["image_url"]
                    ):
                        url = content_item["image_url"]["url"]
                        if url.startswith("data:"):
                            try:
                                # Parse media type and base64 data
                                parts = url.split(";base64,")
                                if len(parts) == 2:
                                    media_type_part, base64_data = parts
                                    media_type = media_type_part.split(":").pop()
                                else:
                                    print(
                                        f"DEBUG - Skipping attachment: Malformed data URL (no ';base64,'): {url[:100]}..."
                                    )
                                    continue

                                decoded_data = base64.b64decode(base64_data)
                                file_size = len(decoded_data)
                                ext = MIME_TO_EXT.get(media_type.split("/")[-1], "bin")
                                filename = (
                                    f"attachment_{len(processed_attachments)}.{ext}"
                                )

                                processed_attachments.append(
                                    {
                                        "filename": filename,
                                        "mimetype": media_type,
                                        "size": file_size,
                                        "decoded_data": decoded_data,
                                    }
                                )
                            except base64.binascii.Error as e:
                                raise Exception(
                                    f"Base64 decode error: {e}. URL: {url[:100]}..."
                                )
                            except Exception as e:
                                print(f"Error processing: {e}")
                    else:
                        raise Exception(
                            f"Unsupported image attachment type: `content_item['type']` === {content_item['type']}"
                        )
            else:
                # Handle plain text content (backward compatibility)
                question = user_message["content"] if user_message else ""
                processed_attachments = []

            try:
                headers = {
                    "Authorization": f"Bearer {self.valves.n8n_bearer_token}",
                }

                if processed_attachments:
                    print("DEBUG - Preparing multipart request")
                    # 1. Prepare metadata for 'filesInput' field
                    filesInput_metadata = [
                        {
                            "filename": att["filename"],
                            "mimetype": att["mimetype"],
                            "size": att["size"],
                        }
                        for att in processed_attachments
                    ]

                    # 2. Prepare form data fields
                    form_data = {
                        "sessionId": f"{chat_id}",
                        self.valves.input_field: question,
                        "filesInput": json.dumps(filesInput_metadata),
                    }
                    print(f"DEBUG - FORM DATA: {form_data}")

                    # 3. Prepare files for upload
                    files_for_upload = {}
                    for i, attachment_info in enumerate(processed_attachments):
                        file_obj = io.BytesIO(attachment_info["decoded_data"])
                        # Use a consistent key like 'file_0', 'file_1' etc. n8n might expect this.
                        # Or use the actual filename if n8n handles it. Let's use 'file_i' for now.
                        file_key = f"file_{i}"
                        files_for_upload[file_key] = (
                            attachment_info["filename"],
                            file_obj,
                            attachment_info["mimetype"],
                        )
                        print(
                            f"DEBUG - Added file to upload: Key='{file_key}', Filename='{attachment_info['filename']}', Mimetype='{attachment_info['mimetype']}'"
                        )

                    # 4. Send multipart request
                    # NOTE: requests sets Content-Type automatically for multipart
                    response = requests.post(
                        self.valves.n8n_url,
                        data=form_data,
                        files=files_for_upload,
                        headers=headers,
                    )
                else:
                    # No attachments, send standard JSON request
                    payload = {
                        "sessionId": f"{chat_id}",
                        self.valves.input_field: question,
                    }
                    headers["Content-Type"] = "application/json"
                    response = requests.post(
                        self.valves.n8n_url, json=payload, headers=headers
                    )

                if response.status_code == 200:
                    response_data = response.json()

                    # Handle case where n8n returns a list
                    if isinstance(response_data, list) and len(response_data) > 0:
                        # Assume the first item contains the relevant data
                        n8n_item_data = response_data[0]
                    elif isinstance(response_data, dict):
                        # n8n returns a dictionary
                        n8n_item_data = response_data
                    else:
                        # Unexpected response format
                        raise Exception(
                            f"Unexpected n8n response format: {type(response_data)}"
                        )

                    # Extract the main response content
                    n8n_response = n8n_item_data.get(
                        self.valves.response_field, "Error: Response field not found"
                    )

                    assistant_message = {"role": "assistant"}

                    if "content" in n8n_item_data:
                        assistant_message["content"] = n8n_item_data["content"]
                    else:
                        assistant_message["content"] = n8n_response

                    body["messages"].append(assistant_message)

                else:
                    raise Exception(f"Error: {response.status_code} - {response.text}")

            except Exception as e:
                await self.emit_status(
                    __event_emitter__,
                    "error",
                    f"Error during sequence execution: {str(e)}",
                    True,
                )
                return {"error": str(e)}
        # If no message is available alert user
        else:
            await self.emit_status(
                __event_emitter__,
                "error",
                "No messages found in the request body",
                True,
            )
            body["messages"].append(
                {
                    "role": "assistant",
                    "content": "No messages found in the request body",
                }
            )

        await self.emit_status(__event_emitter__, "info", "Complete", True)
        return n8n_response
