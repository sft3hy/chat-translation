# app.py

import streamlit as st
import threading
import time

from config import CS_WEBSOCKET_URL
from websocket_client import websocket_thread_runner

# --- Page Configuration ---
# This runs on every page load, making it the perfect place for shared setup.


# --- Thread Management Functions ---
# These are defined here so they can be imported and used by other pages.


def start_websocket_client():
    """Starts the websocket client in a background thread."""
    if (
        "websocket_thread" in st.session_state
        and st.session_state.websocket_thread.is_alive()
    ):
        print("Websocket client is already running, returning.")
        return

    print("Starting websocket client...")
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
    """Stops the websocket client thread gracefully. IMPORTANT: Does not rerun."""
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
        # We REMOVED st.rerun() from here to allow for a clean restart sequence.


def restart_websocket_client():
    """Stops and then starts the websocket client. For applying new room links."""
    st.toast("Restarting client for new room links...", icon="🔄")
    stop_websocket_client()
    # The start function will trigger its own rerun to update the UI
    start_websocket_client()


# --- CHANGE 3: Logic to connect client only on initial load ---
# We use a flag 'client_started' to ensure this block only runs ONCE per session.
if "client_started" not in st.session_state:
    start_websocket_client()
    st.session_state.client_started = True  # Set the flag


# --- CHANGE 1 & 2: Updated Sidebar ---
# This will be displayed on every page of the app.
# The user-facing stop/restart buttons have been removed.

is_running = (
    "websocket_thread" in st.session_state
    and st.session_state.websocket_thread.is_alive()
)

if is_running:
    pass
else:
    st.error("Websocket client is stopped.", icon="❌")
    st.warning(
        "Client is not running. It may be reconnecting or have encountered an error.",
        icon="⚠️",
    )

# --- Main Page Welcome ---


already_linked = st.Page(
    "sidebar/already_linked.py", title="View Rooms", icon=":material/link:"
)
interlink = st.Page(
    "sidebar/new_link.py", title="Create a new linkage", icon=":material/add_link:"
)


pg = st.navigation(
    {"Interlink Rooms": [interlink], "Currently Linked Rooms": [already_linked]}
)

pg.run()
