# app.py

import streamlit as st
import pandas as pd
import uuid
import threading
import time

from config import CS_WEBSOCKET_URL
from utils.cs_helpers import (
    load_json_data,
    save_json_data,
    is_room_name_valid,
    do_two_rooms_exist,
    create_session,
)
from websocket_client import websocket_thread_runner

# --- Page Configuration ---
st.set_page_config(
    page_title="Interlinked",
    page_icon="🔗",
    layout="centered",
    initial_sidebar_state="auto",
)

# --- Constants and File Paths ---
ROOMS_FILE = "data/rooms_for_translating.json"
LANG_CODES_FILE = "data/language_codes.json"
PLACEHOLDER_LANG = "Select a language..."

# --- Thread Management Functions ---


def start_websocket_client():
    """Starts the websocket client in a background thread."""
    if (
        "websocket_thread" in st.session_state
        and st.session_state.websocket_thread.is_alive()
    ):
        st.toast("Client is already running.", icon="ℹ️")
        return

    st.toast("Starting websocket client...", icon="🚀")
    st.session_state.stop_event = threading.Event()
    st.session_state.websocket_thread = threading.Thread(
        target=websocket_thread_runner,
        args=(CS_WEBSOCKET_URL, st.session_state.stop_event),
        daemon=True,
    )
    st.session_state.websocket_thread.start()
    time.sleep(1)  # Give thread time to initialize
    st.rerun()


def stop_websocket_client():
    """Stops the websocket client thread gracefully."""
    if (
        "websocket_thread" in st.session_state
        and st.session_state.websocket_thread.is_alive()
    ):
        st.toast("Stopping websocket client...", icon="🛑")
        st.session_state.stop_event.set()
        st.session_state.websocket_thread.join(timeout=5)
        if st.session_state.websocket_thread.is_alive():
            st.warning("Websocket thread did not stop gracefully.", icon="⚠️")
        del st.session_state.websocket_thread
        del st.session_state.stop_event
        st.rerun()


def restart_websocket_client():
    """Stops and then starts the websocket client."""
    st.toast("Restarting websocket client...", icon="🔄")
    stop_websocket_client()
    # The stop function triggers a rerun, so we just need to start on the next pass


# --- Initialize client on first load ---
if "websocket_thread" not in st.session_state:
    start_websocket_client()

# --- UI: Sidebar for Connection Status ---
with st.sidebar:
    st.header("Connection Status")
    is_running = (
        "websocket_thread" in st.session_state
        and st.session_state.websocket_thread.is_alive()
    )

    if is_running:
        st.success("Client is running.", icon="✅")
        if st.button("Stop Client", use_container_width=True):
            stop_websocket_client()
        if st.button("Restart Client", use_container_width=True):
            restart_websocket_client()
    else:
        st.error("Client is stopped.", icon="❌")
        if st.button("Start Client", use_container_width=True, type="primary"):
            start_websocket_client()

# --- Main Application UI ---
st.title("🔗 Interlinked")
st.markdown(
    """
    Use this tool to create a translation link between two ChatSurfer rooms.
    When a link is created, the websocket client will restart to subscribe to the new rooms.
    """
)
st.divider()

# --- UI: Input Form ---
st.header("Create a New Room Link", anchor=False)

with st.form("link_rooms_form"):
    # Load data for form
    language_data = load_json_data(LANG_CODES_FILE, {})
    language_names = sorted(list(language_data.keys()))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Room 1 Details", anchor=False)
        room1_name = st.text_input(
            "Room 1 Name", placeholder="e.g., project-alpha-support"
        )
        room1_lang = st.selectbox(
            "Room 1 Language", [PLACEHOLDER_LANG] + language_names
        )

    with col2:
        st.subheader("Room 2 Details", anchor=False)
        room2_name = st.text_input(
            "Room 2 Name", placeholder="e.g., soporte-proyecto-alfa"
        )
        room2_lang = st.selectbox(
            "Room 2 Language", [PLACEHOLDER_LANG] + language_names
        )

    st.warning("Room names cannot contain: ` # : , & ' < > \" @ / + `", icon="⚠️")
    submitted = st.form_submit_button(
        "Create Link & Restart Client", type="primary", use_container_width=True
    )

# --- Processing and Validation Logic ---
if submitted:
    errors = []
    if not all([room1_name, room2_name]):
        errors.append("Both room names are required.")
    if not is_room_name_valid(room1_name):
        errors.append(f"Room 1 Name invalid characters.")
    if not is_room_name_valid(room2_name):
        errors.append(f"Room 2 Name invalid characters.")
    if room1_lang == PLACEHOLDER_LANG or room2_lang == PLACEHOLDER_LANG:
        errors.append("Please select a language for both rooms.")
    if room1_name and room1_name == room2_name:
        errors.append("Room names must be unique.")

    if not errors:
        with st.spinner("Checking if rooms exist..."):
            if not do_two_rooms_exist(room1_name, room2_name, create_session()):
                errors.append("One or both rooms do not exist. Please check spelling.")

    if errors:
        for error in errors:
            st.error(error, icon="🚨")
    else:
        # All checks passed, create the link
        new_pair = {
            "pairId": str(uuid.uuid4()),
            "room1name": room1_name,
            "room2name": room2_name,
            "room1lang": room1_lang,
            "room2lang": room2_lang,
        }

        rooms_data = load_json_data(ROOMS_FILE, {"rooms": []})
        rooms_data["rooms"].append(new_pair)
        save_json_data(ROOMS_FILE, rooms_data)

        st.success(f"Successfully linked '{room1_name}' and '{room2_name}'!", icon="✅")
        st.balloons()

        # This is the key part: restart the client to pick up new rooms
        restart_websocket_client()

# --- UI: Display Current State ---
st.divider()
st.header("Currently Linked Rooms", anchor=False)
rooms_data = load_json_data(ROOMS_FILE, {"rooms": []})

if rooms_data["rooms"]:
    df = pd.DataFrame(rooms_data["rooms"])
    df_display = df.rename(
        columns={
            "pairId": "Pair ID",
            "room1name": "Room 1",
            "room1lang": "Lang 1",
            "room2name": "Room 2",
            "room2lang": "Lang 2",
        }
    )
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("No rooms have been linked yet.", icon="ℹ️")
