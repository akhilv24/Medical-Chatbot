# from dotenv import load_dotenv
# load_dotenv()
# import streamlit as st
# from langchain_groq import ChatGroq
# from langchain.chat_models import init_chat_model
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain

# def query(Input):
#     llm = ChatGroq(model="llama-3.1-8b-instant")


#     prompt = PromptTemplate.from_template("You are a cardiologist , Explain the {Input} in simple terms ")
#     Chain = LLMChain(llm=llm,prompt=prompt)

#     return Chain.run(Input)

# st.set_page_config(page_title="Medical Chatbot")
# st.title("Medical Chatbot")

# user_input = st.text_input("Ask a health-related question:")

# if st.button("Get Answer"):
#     if user_input:
#         prompt = PromptTemplate.from_template("You are a cardiologist , Explain the {topic} in simple terms ")
#         answer = query({"inputs": prompt})
#         st.success(f"MedBot: {answer}")
#     else:
#         st.warning("Please enter a question.")

import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import speech_recognition as sr
from datetime import datetime

# --- LangChain (NEW API) ---
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import json
from pathlib import Path

from medicine_info import load_medicine_data, fetch_medicine_info
from health_dashboard import show_health_dashboard 
from medicine_reminder import add_reminder, get_due_reminders, clear_all_reminders, play_reminder_audio



#       ENV + MODEL SETUP
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(model_name="llama-3.1-8b-instant")

# Medicine dataset
medicine_df = load_medicine_data()

# Prompt (NEW LangChain format)
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are Medic-Bot, a friendly and knowledgeable medical assistant. "
     "Always talk in a simple, clear way."),
    ("human", "{question}")
])

# New Chain (Runnable Pipeline)
chain = prompt | llm | StrOutputParser()


#       VOICE INPUT
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info(" Listening...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError:
        return "Voice service is unavailable."


#      SAVE + LOAD CHATS
def save_chat(chat_history):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Path("chats").mkdir(exist_ok=True)
    with open(f"chats/chat_{timestamp}.json", "w") as f:
        json.dump(chat_history, f, indent=4)

def load_saved_chats():
    Path("chats").mkdir(exist_ok=True)
    files = list(Path("chats").glob("chat_*.json"))
    return sorted(files, reverse=True)

def load_chat(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


#          UI LAYOUT
st.set_page_config(page_title="Medic-Bot", layout="centered")

col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/chatbot.png", width=200)
with col2:
    st.markdown("<h1 style='padding-top: 8px;'>Medic-Bot — AI Health Assistant</h1>", unsafe_allow_html=True)

st.markdown("I'm here to help you with your health-related queries.")

# Suggested prompts
st.markdown("##### Try asking:")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("What causes high BP?"):
        st.session_state.spoken_input = "What causes high blood pressure?"
with col2:
    if st.button("Prevent diabetes"):
        st.session_state.spoken_input = "How can I prevent diabetes?"
with col3:
    if st.button("Tips for healthy heart"):
        st.session_state.spoken_input = "Tips for maintaining a healthy heart"


#     MEDICINE REMINDER UI
with st.expander(" Set a Medicine Reminder"):
    med_name = st.text_input("Medicine Name")
    dosage = st.text_input("Dosage (e.g., 1 tablet)")
    time_input = st.time_input("Reminder Time")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add Reminder!!!"):
            if med_name and dosage:
                add_reminder(med_name, time_input.strftime("%H:%M"), dosage)
                st.success(f"Reminder set for **{med_name}** at {time_input.strftime('%H:%M')}")
            else:
                st.error("Please fill all fields.")

    with col2:
        if st.button(" Clear All Reminders"):
            clear_all_reminders()
            st.warning("All reminders cleared.")


#     SESSION STATE SETUP
if "spoken_input" not in st.session_state:
    st.session_state.spoken_input = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_medicine_reply" not in st.session_state:
    st.session_state.last_medicine_reply = ""


# Sidebar for saved chats
with st.sidebar:
    st.markdown("## Chat History")
    chat_files = load_saved_chats()
    chat_names = [f.name for f in chat_files]
    selected_chat = st.selectbox("Load Chat:", ["None"] + chat_names)
    if selected_chat != "None":
        loaded_chat = load_chat(f"chats/{selected_chat}")
        st.session_state.chat_history = loaded_chat
        st.success(f"Loaded: {selected_chat}")

# Sidebar Features
page = st.sidebar.selectbox("Choose Feature", ["Chat", "Medicine Info", "Health Stats Dashboard"])

if page == "Health Stats Dashboard":
    show_health_dashboard()


#       INPUT SECTION
user_input = st.text_input(
    " Ask your medical question:",
    value=st.session_state.spoken_input,
    key="main_input"
)

col_voice, col_submit = st.columns([1, 2])

with col_voice:
    if st.button(" Speak"):
        spoken = listen()
        st.session_state.spoken_input = spoken
        st.success(f"You said: {spoken}")

with col_submit:
    if st.button(" Get Answer"):
        final = user_input.strip()
        if final:
            response = chain.invoke({"question": final})
            st.session_state.chat_history.append(("You", final))
            st.session_state.chat_history.append(("Medic-Bot", response))
            st.session_state.spoken_input = ""
            save_chat(st.session_state.chat_history)
            st.success(" Answered by Medic-Bot")
        else:
            st.warning("Please enter or speak something first.")


#      MEDICINE INFO BUTTON
if st.button(" Medicine Info"):
    query = st.session_state.get("spoken_input") or user_input
    if query.strip():
        med_info = fetch_medicine_info(medicine_df, query)
        st.image("medi.png", width=50)
        st.markdown(med_info)

        if med_info:
            st.session_state.last_medicine_reply = med_info
            st.session_state.chat_history.append(("You", query))
            st.session_state.chat_history.append(("Medic-Bot", med_info))
            st.success("Found medicine info")
        else:
            fallback = chain.invoke({"question": query})
            st.session_state.last_medicine_reply = fallback
            st.session_state.chat_history.append(("You", query))
            st.session_state.chat_history.append(("Medic-Bot", fallback))
            st.success("Answered by Medic-Bot")
    else:
        st.warning("Please provide a query first.")


#     DISPLAY LAST MED INFO
if st.session_state.last_medicine_reply:
    st.divider()
    st.markdown(
        f"<div style='color:#CDE6D0;padding:10px;border-radius:10px;background:#111827;margin-bottom:5px;'>"
        f"<b>Medic-Bot:</b><br>{st.session_state.last_medicine_reply}</div>",
        unsafe_allow_html=True
    )


#     CHAT HISTORY DISPLAY
if st.session_state.chat_history:
    st.divider()

    for role, msg in reversed(st.session_state.chat_history):
        if role == "You":
            st.markdown(
                f"<div style='color:#E1E1E1;padding:8px;border-radius:10px;background:#1f2937;margin-bottom:5px;'><b>You:</b> {msg}</div>",
                unsafe_allow_html=True
            )
        else:
            if msg != st.session_state.last_medicine_reply:
                st.markdown(
                    f"<div style='color:#CDE6D0;padding:8px;border-radius:10px;background:#111827;margin-bottom:5px;'><b>Medic-Bot:</b> {msg}</div>",
                    unsafe_allow_html=True
                )
