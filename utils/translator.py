from google.cloud import translate
import json
from config import *
from utils.cs_helpers import send_public_message, create_session


def translate_text(text="I", translate_from="en", translate_to="ko"):
    project_id = "cs-autotranslation"
    client = translate.TranslationServiceClient()
    location = "global"
    parent = f"projects/{project_id}/locations/{location}"

    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",
            "source_language_code": translate_from,
            "target_language_code": translate_to,
        }
    )

    for translation in response.translations:
        return translation.translated_text


def recreate_room_lookups():
    # Load room pair configuration
    with open("data/rooms_for_translating.json", "r") as f:
        room_pairs = json.load(f)["rooms"]
    f.close()

    with open("data/language_codes.json", "r") as f:
        codes = json.load(f)
    f.close()

    # Build a lookup for both directions
    room_lookup = {}
    for pair in room_pairs:
        room_lookup[pair["room1name"]] = {
            "target_room": pair["room2name"],
            "from_lang": codes[pair["room1lang"]],
            "to_lang": codes[pair["room2lang"]],
        }
        room_lookup[pair["room2name"]] = {
            "target_room": pair["room1name"],
            "from_lang": codes[pair["room2lang"]],
            "to_lang": codes[pair["room1lang"]],
        }
    return room_lookup


def translation_module(cs_message: dict):
    room_name = cs_message["roomName"]
    room_lookup = recreate_room_lookups()
    if room_name in room_lookup:
        config = room_lookup[room_name]

        print(
            f"Translating text: {cs_message["text"][:20]} from {config['from_lang']} to {config['to_lang']}"
        )

        translated_text = translate_text(
            text=cs_message["text"],
            translate_from=config["from_lang"],
            translate_to=config["to_lang"],
        )

        t_message = " (from Google Translate)"
        send_public_message(
            message_text=translated_text,
            message_id=cs_message["id"],
            session_id=create_session(),
            nickName=cs_message["sender"] + t_message,
            roomName=config["target_room"],
            thread=False,
        )


sample_message = {
    "classification": "UNCLASSIFIED//FOUO",
    "clearance": "U",
    "dissemControls": ["FOUO"],
    "domainId": "chatsurferxmppunclass",
    "id": "01ef5365-b612-0062-b452-c38df1540975",
    "networkId": "unclass",
    "requiredDissemMatches": 1,
    "requiredFaMatches": 0,
    "roomName": "translate_en_es",
    "sender": "slammy",
    "text": "hello",
    "timestamp": "2024-08-05T20:02:58.321Z",
    "userId": "aa8f8426-c46c-416d-ae85-5683f0b94b03",
    "private": False,
}

# translation_module(sample_message)
