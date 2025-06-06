# websocket_client.py

import asyncio
import json
import logging
import ssl
import time
from uuid import uuid4
import re
import websockets
from config import BOT_USER_ID, CA_BUNDLE_PATH, CERT_PATH, KEY_PATH
from utils.cs_helpers import create_session, get_private_rooms
from utils.translator import translation_module

# Set up logging
logger = logging.getLogger("websockets")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# A unique string to temporarily replace escaped quotes during parsing
QUOTECODE = str(uuid4())


async def connect_and_subscribe(uri: str, stop_event: asyncio.Event):
    """
    Connects to the websocket, subscribes to topics, and processes messages.
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(CA_BUNDLE_PATH)
    ssl_context.load_cert_chain(CERT_PATH, KEY_PATH)

    session_id = create_session()
    headers = {"Cookie": f"SESSION={session_id}"}

    private_rooms_list = get_private_rooms(session_id)
    new_priv_rooms = {}
    count = 0

    try:
        async with websockets.connect(
            uri, ssl=ssl_context, extra_headers=headers
        ) as websocket:
            logger.info("Successfully connected to websocket.")

            # STOMP CONNECT frame
            await websocket.send(
                '["CONNECT\\naccept-version:1.2\\nheart-beat:0,0\\n\\n\\u0000"]'
            )

            # Basic Subscriptions
            subscriptions = {
                "all-messages": "/topic/chat-messages-all",
                "direct-messages": "/user/topic/direct-message",
                "room-updates": "/user/topic/room-membership-changed-event",
            }
            for key, dest in subscriptions.items():
                await websocket.send(
                    f'["SUBSCRIBE\\nid:sub-{count}\\ndestination:{dest}\\n\\n\\u0000"]'
                )
                count += 1

            # Subscribe to initial private rooms
            for room_name in private_rooms_list:
                new_priv_rooms[room_name] = count
                sub_frame = f'["SUBSCRIBE\\nid:sub-{count}\\ndestination:/topic/chat-messages-room/chatsurferxmppunclass/{room_name}\\n\\n\\u0000"]'
                await websocket.send(sub_frame)
                count += 1

            logger.info("Subscriptions sent. Listening for messages...")

            while not stop_event.is_set():
                try:
                    # The timeout allows the loop to periodically check the stop_event
                    stomp_message = await asyncio.wait_for(
                        websocket.recv(), timeout=1.0
                    )
                    await process_stomp_message(
                        stomp_message, websocket, new_priv_rooms
                    )
                except asyncio.TimeoutError:
                    # No message received, continue loop to check stop_event again
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Websocket connection closed.")
                    break

    except Exception as e:
        logger.error(f"Websocket connection error: {e}")
    finally:
        logger.info("Websocket client coroutine finished.")


async def process_stomp_message(stomp_message, websocket, new_priv_rooms):
    """Parses and acts on a single STOMP message from the server."""
    # Ignore initial connection confirmation and heartbeats
    if "CONNECTED" in stomp_message or stomp_message == "o":
        return

    try:
        # A more robust way to find the JSON part of a STOMP message
        json_part_match = re.search(r"(\{.+\})", stomp_message)
        if not json_part_match:
            return

        # Clean and parse JSON
        json_str = (
            json_part_match.group(1).replace('\\\\\\"', QUOTECODE).replace("\\", "")
        )
        parsed_dict = json.loads(json_str)

        # Handle direct messages by normalizing their structure
        is_dm = "message" in parsed_dict and "contactUserId" in parsed_dict
        if is_dm:
            parsed_dict = parsed_dict["message"]
            parsed_dict["userId"] = parsed_dict.get("senderUserId")

        if "text" in parsed_dict:
            parsed_dict["text"] = parsed_dict["text"].replace(QUOTECODE, '"')

        # Handle room membership changes
        if "changedMembershipType" in parsed_dict:
            room_name = parsed_dict.get("roomName")
            if parsed_dict["changedMembershipType"] == "FOLLOWER" and parsed_dict.get(
                "privateRoom"
            ):
                logger.info(f"Bot added to private room: {room_name}")
                # Dynamically subscribe to new room (optional, restart is safer)
            elif parsed_dict["changedMembershipType"] == "NONE" and parsed_dict.get(
                "privateRoom"
            ):
                logger.info(f"Bot removed from room: {room_name}")
                # Dynamically unsubscribe (optional, restart is safer)

        # Process translatable messages
        is_bot_message = parsed_dict.get("userId") == BOT_USER_ID
        has_required_fields = all(k in parsed_dict for k in ["userId", "text"]) and (
            "roomName" in parsed_dict or is_dm
        )

        if not is_bot_message and has_required_fields:
            translation_module(parsed_dict)

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from message: {stomp_message}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def websocket_thread_runner(uri: str, stop_event: asyncio.Event):
    """The target function for the background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while not stop_event.is_set():
        try:
            # Run the client. This will block until the connection is lost.
            loop.run_until_complete(connect_and_subscribe(uri, stop_event))
            if not stop_event.is_set():
                logger.info("Connection lost. Reconnecting in 5 seconds...")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error in websocket runner: {e}. Retrying in 10 seconds.")
            time.sleep(10)
