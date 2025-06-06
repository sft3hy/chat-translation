import time
import requests
import re
import json
from config import *

SESSION_EXPIRATION_TIME = (
    60 * 60
)  # 1 hour before we expire the old session and get a new one


def load_json_data(filepath, default_data):
    """Safely loads a JSON file, creating it with default data if it doesn't exist."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_json_data(filepath, default_data)
        return default_data


def save_json_data(filepath, data):
    """Saves data to a JSON file with pretty printing."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- Validation Helper ---

INVALID_ROOM_CHARS_REGEX = re.compile(r"[#:,&'<>\"@/+]")


def is_room_name_valid(name):
    """Checks if a room name contains any forbidden characters."""
    return not INVALID_ROOM_CHARS_REGEX.search(name)


def get_thread(message_id: str, roomName: str, session_id: str):
    url = f"https://{CS_HOST}/api/chat/messages/chatsurferxmppunclass/{roomName}?threadId={message_id}"
    headers = {
        "Content-type": "application/json",
    }
    cook = {"SESSION": session_id}
    send = requests.get(
        url,
        cert=(CERT_PATH, KEY_PATH),
        verify=CA_BUNDLE_PATH,
        headers=headers,
        cookies=cook,
    )
    if "messages" in send.json():
        threaded_messages = send.json()["messages"]
    else:
        return "noThread"
    last_message = threaded_messages[-1]
    # print('last message from method get_thread:', last_message)
    if "threadId" in last_message.keys():  # thread exists for this message
        new_url = f"https://{CS_HOST}/api/chat/messages/chatsurferxmppunclass/{roomName}?threadId={last_message['threadId']}"
        whole_thread = requests.get(
            new_url,
            cert=(CERT_PATH, KEY_PATH),
            verify=CA_BUNDLE_PATH,
            headers=headers,
            cookies=cook,
        ).json()["messages"]
        return {"whole_thread": whole_thread, "thread_id": last_message["threadId"]}
    else:
        return "noThread"


def get_last_five_dms(user_id: str, session_id: str):

    url = f"https://chatsurfer.nro.mil/api/directmessage/contacts/{user_id}/messages?commonClassification=UNCLASSIFIED%2F%2FFOUO"
    cook = {"SESSION": session_id}
    send = requests.get(
        url, cert=(CERT_PATH, KEY_PATH), verify=CA_BUNDLE_PATH, cookies=cook
    )
    formatted_for_gemini = ""
    last_five = send.json()["messages"][:5]
    last_five.reverse()
    for message in last_five:
        if message["senderUserId"] == "27fbef28-0663-4659-b479-ca8cd555e013":
            formatted_for_gemini += "Cosmic Gemini: " + message["text"] + "\n"
        else:
            formatted_for_gemini += "User: " + message["text"] + "\n"
    return formatted_for_gemini.strip()


# get_last_five_dms('b64aa790-6736-4d0f-a164-10235234867e', '7b8b594d-8b25-452a-8c95-a7d7518dc7f9')


def send_public_message(
    message_text: str,
    roomName: str,
    message_id: str,
    session_id: str,
    thread=True,
    classification: str = "UNCLASSIFIED//FOUO",
    domainId: str = "chatsurferxmppunclass",
    nickName: str = "AskSlammy",
):
    headers = {
        "Content-type": "application/json",
    }
    # if TEST == "True":
    #     nickName = "slammyLocalTest"
    message = {
        "classification": classification,
        "message": message_text,
        "domainId": domainId,
        "nickName": nickName,
        "roomName": roomName,
    }
    cook = {"SESSION": session_id}

    url = "https://" + CS_HOST + "/api/chatserver/message?api-key=" + CHATKEY

    if thread:
        message["files"] = []
        thread_message_id = message_id
        whole_thread = get_thread(
            roomName=roomName, message_id=message_id, session_id=session_id
        )
        if whole_thread != "noThread":
            thread_message_id = whole_thread["thread_id"]
        url = f"https://{CS_HOST}/api/thread/thread/{thread_message_id}/reply"

    send = requests.post(
        url,
        cert=(CERT_PATH, KEY_PATH),
        verify=CA_BUNDLE_PATH,
        headers=headers,
        json=message,
        cookies=cook,
    )
    print(f"Response from ChatSurfer send public message: {send}")


def send_dm(message_text: str, user_id: str, session_id: str):
    headers = {
        "Content-type": "application/json",
    }
    message = {
        "classification": "UNCLASSIFIED//FOUO",
        "files": [],
        "instanceId": "unclass-prod",
        "text": message_text,
    }
    cook = {"SESSION": session_id}

    url = f"https://{CS_HOST}/api/directmessage/contacts/{user_id}/messages"

    send = requests.post(
        url,
        cert=(CERT_PATH, KEY_PATH),
        verify=CA_BUNDLE_PATH,
        headers=headers,
        json=message,
        cookies=cook,
    )
    print(f"Response from ChatSurfer send DM: {send}")


def session_request():
    clear_sessions()
    print("session expired, creating new session")
    url = "https://" + CS_HOST + "/api/auth/newsession"
    headers = {
        "Content-type": "application/json",
    }
    json_data = {
        "apiKey": CHATKEY,
    }
    session_response = requests.post(
        url,
        cert=(CERT_PATH, KEY_PATH),
        headers=headers,
        json=json_data,
        verify=CA_BUNDLE_PATH,
    )
    tries = 5
    while session_response.status_code > 204 and tries > 0:
        if (
            "Set-Cookie" in session_response.headers
            and session_response.headers["Set-Cookie"].split(";")[0] != "SESSION="
        ):
            break
        else:
            session_response = requests.post(
                url,
                cert=(CERT_PATH, KEY_PATH),
                headers=headers,
                json=json_data,
                verify=CA_BUNDLE_PATH,
            )
            time.sleep(1)
            tries -= 1
    session_id = session_response.headers["Set-Cookie"].split(";")[0].split("=")[1]
    with open("data/session_created.txt", "w") as f:
        f.write(f"{time.time()+(SESSION_EXPIRATION_TIME)}separator1234{session_id}")
    print("got session:", session_id)
    return session_id


def create_session():
    with open("data/session_created.txt", "r") as f:
        text = f.read()
    if "separator1234" in text:
        info = text.split("separator1234")
        if time.time() > float(info[0]) or info[1] == "":
            session_id = session_request()
        else:
            print("using existing session:", info[1])
            session_id = info[1]
    else:
        session_id = session_request()
    return session_id


def clear_sessions():
    url = "https://" + CS_HOST + "/api/auth/clearsessions?api-key=" + CHATKEY
    clear = requests.post(url, cert=(CERT_PATH, KEY_PATH), verify=CA_BUNDLE_PATH)
    tries = 5
    while clear.status_code > 204 and tries > 0:
        clear = requests.post(url, cert=(CERT_PATH, KEY_PATH), verify=CA_BUNDLE_PATH)
        time.sleep(1)
        tries -= 1


def get_private_rooms(session_id: str):
    url = f"https://{CS_HOST}/api/roommembership/rooms/private"
    cook = {"SESSION": session_id}

    priv_rooms_raw = requests.get(
        url, cert=(CERT_PATH, KEY_PATH), verify=CA_BUNDLE_PATH, cookies=cook
    ).json()
    private_rooms_list = []
    if "privateRooms" in priv_rooms_raw.keys():
        for room in priv_rooms_raw["privateRooms"]:
            private_rooms_list.append(room["roomName"])
        return private_rooms_list


def do_two_rooms_exist(room_name1: str, room_name2: str, session_id: str):
    url = f"https://{CS_HOST}/api/roomsearch/rooms/search"
    cook = {"SESSION": session_id}
    pageNumber = 0
    total_rooms_count = float("inf")
    rooms_list = []
    room_found = False
    while pageNumber * 500 < total_rooms_count and pageNumber < 100:
        print(
            f"browsing page {pageNumber} for {room_name1} and {room_name2} to see if they are a valid rooms..."
        )
        payload = {
            "sortCriteria": {
                "orders": [{"sortField": "FIRST_JOINED_DATE", "sortDirection": "DESC"}]
            },
            "keywordCriteria": {"searchFields": ["DISPLAY_NAME"], "query": ""},
            "aboveUserDefaultHighOptIn": True,
            "includePrivateRooms": True,
            "pageNumber": pageNumber,
            "pageSize": 500,
        }

        rooms_raw = requests.post(
            url,
            cert=(CERT_PATH, KEY_PATH),
            verify=CA_BUNDLE_PATH,
            cookies=cook,
            json=payload,
        ).json()
        total_rooms_count = rooms_raw.get("totalRoomCount")
        for room in rooms_raw.get("rooms"):
            rooms_list.append(room["roomName"])
        pageNumber += 1
        time.sleep(0.2)

        if room_name1 in rooms_list and room_name2 in rooms_list:
            print("found rooms!")
            room_found = True
            break

    with open("data/found_some_cs_rooms.json", "w") as file:
        json.dump(rooms_list, file, indent=4)
    return room_found


# do_two_rooms_exist("translate_es_en", "translate_en_es", create_session())
