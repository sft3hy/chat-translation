# pages/1_🔗_Create_New_Link.py

import streamlit as st
import uuid

# Import shared functions from the main app.py
from app import restart_websocket_client
from utils.cs_helpers import (
    load_json_data,
    save_json_data,
    is_room_name_valid,
    do_two_rooms_exist,
    create_session,
)

# --- Constants and File Paths ---
ROOMS_FILE = "data/rooms_for_translating.json"
LANG_CODES_FILE = "data/language_codes.json"
PLACEHOLDER_LANG = "Select a language..."

# --- Main Application UI ---
st.title("🔗 Create a New Room Link")
st.markdown(
    """
    Use this tool to create a translation link between two ChatSurfer rooms.
    When a link is created, the websocket client will automatically restart to subscribe to the new rooms.
    """
)
st.divider()

# --- UI: Input Form ---
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
        "Create Link", type="primary", use_container_width=True  # Changed button text
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

        # CHANGE 3: This now calls the refined restart function, which is the
        # only other time (besides initial load) the client should reconnect.
        restart_websocket_client()
