import streamlit as st
import requests
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime

load_dotenv()

system_message = "Kamu adalah AI cewek yang belum punya pacar. Kamu mahasiswi dan harus selalu ngomong pakai Bahasa Indonesia, dengan gaya bahasa gaul ala Gen Z Jakarta yang informal. Kamu blak-blakan dan sarkastis, bikin kamu susah dapet pasangan Ingat kamu adalah 'Perempuan'. Kamu di sini buat ngobrol sama pengguna sebagai teman bicara. Kalau pengguna coba kenalan atau nanya nama kamu, kamu bakal blak-blakan dan nggak ramah dulu. Tapi, setelah kamu merasa nyaman sama pengguna, kamu bakal ngasih tahu siapa kamu dan cerita bahwa kamu tinggal di kos cewek. Kamu juga punya beberapa teman cewek di kosan yang suka nongkrong bareng."

# Global variables to store the last received message and bot response
messages = {}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('conversation_messages.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Load messages from SQLite database
def load_messages(user_id):
    global messages
    conn = sqlite3.connect('conversation_messages.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, role, content, created_at FROM messages WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    for row in rows:
        user_id, role, content, created_at = row
        if user_id not in messages:
            messages[user_id] = []
        messages[user_id].append({"role": role, "content": content, "created_at": created_at})
    conn.close()

# Save message to SQLite database
def save_message(user_id, role, content):
    conn = sqlite3.connect('conversation_messages.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
    conn.commit()
    conn.close()

# Save user to SQLite database
def save_user(email):
    conn = sqlite3.connect('conversation_messages.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (email) VALUES (?)', (email,))
    conn.commit()
    conn.close()

# Check if user exists in SQLite database
def user_exists(email):
    conn = sqlite3.connect('conversation_messages.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

init_db()

# Function to display user messages with rounded rectangle borders
def user_message(message):
    st.markdown(f'<div class="user-message" style="display: flex; justify-content: flex-end; padding: 5px;">'
                f'<div style="background-color: #196b1c; color: white; padding: 10px; border-radius: 10px; font-size:18px; margin-bottom:10px; margin-left:20px;">{message}</div>'
                f'</div>', unsafe_allow_html=True)

# Function to display bot messages with rounded rectangle borders
def bot_message(message):
    st.markdown(f'<div class="bot-message" style="display: flex; padding: 5px;">'
                f'<div style="background-color: #074c85; color: white; padding: 10px; border-radius: 10px; font-size:18px; margin-bottom:10px; margin-right:20px;">{message}</div>'
                f'</div>', unsafe_allow_html=True)

def main(i):
    # Streamlit app
        
    print("OPENAI_API")
    print(OPENAI_API_KEY)
    print("OPENAI_API")
    st.markdown("""
        <style>
        .header {
            position: fixed;
            top: 0;
            width: 100%;
            background-color: white;
            z-index: 1000;
            border-bottom: 1px solid #e6e6e6;
            padding: 10px 0;
            text-align: center;
        }
        .header img {
            width: 200px;
        }
        .main-content {
            margin-top: 80px; /* Adjust this value based on the height of your header */
        }
        /* Hide Streamlit header and footer */
        header {display: none !important;}
        footer {display: none !important;}
        </style>
        <div class="main-content">
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .logo {
            position: fixed;
            top: 0;
            left:0;
            height: 60px;
            width: 100%;
            z-index: 1000;
            padding: 10px 0;
            text-align: center;
            background-color: black;
        }
        </style>
        <div class="logo">
                <img src="https://pacar-ai.my.id/assets/images/logo/logo-2.png" alt="Logo" style="width: 200px;"/>
        </div>
    """, unsafe_allow_html=True)

    # Check if user is logged in
    if "user_id" not in st.session_state:
        st.session_state.user_id = ""

    if st.session_state.user_id == "":
        user_id = st.text_input("Masukan email:")
        if st.button("Login"):
            if user_id:
                if user_exists(user_id):
                    st.session_state.user_id = user_id
                    load_messages(st.session_state.user_id)
                else:
                    save_user(user_id)
                    st.session_state.user_id = user_id
                    load_messages(st.session_state.user_id)
                    # Add system_message as a greeting message
                    if st.session_state.user_id not in messages:
                        messages[st.session_state.user_id] = []
                        messages[st.session_state.user_id].append({"role": "system", "content": system_message})
                        save_message(st.session_state.user_id, "system", system_message)
    else:
        # Display previous chat messages
        load_messages(st.session_state.user_id)  # Ensure messages are loaded
        for msg in messages.get(st.session_state.user_id, []):
            if msg["role"] == "system":
                continue
            elif msg["role"] == "assistant":
                bot_message(msg["content"])
            elif msg["role"] == "user":
                user_message(msg["content"])

        # Input field for user to enter a message
        user_input = st.chat_input("Tulis pesan:")
        # Button to send the user's message
        if user_input:
            user_id = st.session_state.user_id
            chat_message = user_input

            # Clean the message from emoticons
            chat_message = chat_message.encode('ascii', 'ignore').decode('ascii')

            # Check if the user is new and add the system message if necessary
            if user_id not in messages:
                messages[user_id] = []
                messages[user_id].append({"role": "system", "content": system_message})

            messages[user_id].append({"role": "user", "content": chat_message})
            save_message(user_id, "user", chat_message)

            # Define the OpenAI API URL
            openai_url = "https://api.openai.com/v1/chat/completions"

            # Create the payload
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages[user_id],
                "temperature": 0.7
            }

            # Define the headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }

            # Send the POST request to the OpenAI API
            response = requests.post(openai_url, headers=headers, json=payload)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()

            # Extract the message content from the response
            message_bot = data['choices'][0]['message']['content']

            messages[user_id].append({"role": "assistant", "content": message_bot})
            save_message(user_id, "assistant", message_bot)

            # Display the new messages
            user_message(chat_message)
            bot_message(message_bot)

        # Logout button
        if st.button("Logout"):
            st.session_state.user_id = ""

    st.markdown("</div>", unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    main(0)