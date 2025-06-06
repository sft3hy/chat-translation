# pages/2_📊_Currently_Linked_Rooms.py

import streamlit as st
import pandas as pd
from utils.cs_helpers import load_json_data

# --- Constants ---
ROOMS_FILE = "data/rooms_for_translating.json"

# --- UI: Display Current State ---
st.title("📊 Currently Linked Rooms")
st.markdown(
    "This page shows all the room-to-room translation links that are currently active."
)
st.divider()

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
