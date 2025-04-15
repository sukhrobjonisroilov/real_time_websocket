import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import OpenAI

app = FastAPI()

# Initialize DeepSeek client
client = OpenAI(api_key="sk-f6771a27bec64ac19dd9ccfb44f31885", base_url="https://api.deepseek.com")

class ChatWebSocket:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.message_history = []  # Store conversation history in memory for this connection

    async def connect(self):
        await self.websocket.accept()

    async def disconnect(self):
        pass  # No cleanup needed since no persistent storage or groups

    async def receive(self, text_data: str):
        try:
            text_data_json = json.loads(text_data)
            user_message = text_data_json.get("message")
            if not user_message:
                await self.websocket.send_json({"error": "Message is required"})
                return

            # Get DeepSeek response
            assistant_reply = await self.get_deepseek_response(user_message)

            # Store messages in memory for this connection
            self.message_history.append({"role": "user", "content": user_message})
            self.message_history.append({"role": "assistant", "content": assistant_reply})

            # Send messages back to client
            await self.websocket.send_json({"role": "user", "message": user_message})
            await self.websocket.send_json({"role": "assistant", "message": assistant_reply})

        except json.JSONDecodeError:
            await self.websocket.send_json({"error": "Invalid JSON format"})
        except Exception as e:
            await self.websocket.send_json({"error": str(e)})

    async def get_deepseek_response(self, user_message: str) -> str:
        # Include conversation history in the DeepSeek request
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
        ] + self.message_history + [
            {"role": "user", "content": user_message}
        ]
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    chat = ChatWebSocket(websocket)
    await chat.connect()
    try:
        while True:
            data = await websocket.receive_text()
            await chat.receive(data)
    except WebSocketDisconnect:
        await chat.disconnect()
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()