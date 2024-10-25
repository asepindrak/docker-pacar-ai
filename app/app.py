from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store the last received message and bot response
last_received_message = {}
last_bot = {}
token = os.getenv("GRAPH_API_TOKEN")
webhook_verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN")
port = int(os.getenv("PORT", 8000))
messages = {}

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # check the mode and token sent are correct
    if mode == "subscribe" and token == webhook_verify_token:
        print("Webhook verified successfully!")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook")
async def webhook(request: Request):
    global last_received_message
    global last_bot
    global messages
    try:
        # log incoming messages
        body = await request.json()
        print("Incoming webhook message:", body)

        # check if the webhook request contains a message
        message = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0]
        from_number = message.get("from")
        to_number = message.get("to")
        message_id = message.get("id")
        chat_message = message.get("text", {}).get("body")

        # check if the incoming message contains text
        if message.get("type") == "text":
            # extract the business number to send the reply from it
            business_phone_number_id = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("metadata", {}).get("phone_number_id")
            url = f"https://graph.facebook.com/v21.0/{business_phone_number_id}/messages"

            # Check if the current chat_message is the same as the last one
            if (chat_message == last_received_message.get(from_number) or chat_message == last_bot.get(from_number)) and chat_message.lower() != "sayang":
                print("Duplicate message!")
                return JSONResponse(content={"status": "ignored", "message": "Duplicate message"}, status_code=200)

            last_received_message[from_number] = chat_message

            # Clean the message from emoticons
            chat_message = chat_message.encode('ascii', 'ignore').decode('ascii')

            # Mark incoming message as read
            print("Mark incoming message as read...")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            check_message = chat_message.lower()
            # Check if the message is a greeting and remove all characters except alphabets
            if check_message == "sayang":
                messages[from_number] = []
                message_bot = "iyaa sayang.."
                messages[from_number].append({"role": "user", "content": check_message})
                messages[from_number].append({"role": "assistant", "content": message_bot})
                print("New conversation started...")
                # Send the response back to the WhatsApp API
                payload = {
                    "messaging_product": "whatsapp",
                    "to": from_number,
                    "type": "text",
                    "text": {
                        "preview_url": True,
                        "body": message_bot
                    }
                }
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                # Create log txt to save the conversation history by user
                with open(f"conversation_{from_number}.txt", "w", encoding="utf-8") as f:
                    for msg in messages[from_number]:
                        f.write(f"{msg['role']}: {msg['content']}\n")
                return JSONResponse(content={"status": "ignored", "message": "New conversation started..."}, status_code=200)

            # Send the message to the AI model
            if from_number not in messages:
                messages[from_number] = []

            messages[from_number].append({"role": "user", "content": chat_message})
            print(messages[from_number])
            print("Sending message to AI model...")
            ai_url = "http://localhost:11434/api/chat"
            payload = {
                "model": "adens/ai-girlfriend",
                "messages": messages[from_number],
                "stream": False,
            }

            response = requests.post(ai_url, json=payload)
            response.raise_for_status()

            # Print the response for debugging
            data = response.json()

            message_bot = data['message']['content']
            messages[from_number].append({"role": "assistant", "content": message_bot})
            # Create log txt to save the conversation history by user
            with open(f"conversation_{from_number}.txt", "w", encoding="utf-8") as f:
                for msg in messages[from_number]:
                    f.write(f"{msg['role']}: {msg['content']}\n")

            if data['done']:
                print(message_bot)
                
                # Update the last bot message
                last_bot[from_number] = message_bot

                # Send the response back to the WhatsApp API
                payload = {
                    "messaging_product": "whatsapp",
                    "to": from_number,
                    "type": "text",
                    "text": {
                        "preview_url": True,
                        "body": message_bot
                    }
                }
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                # Print response log
                print(response.json())
                return JSONResponse(content={"status": "success"}, status_code=200)
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)