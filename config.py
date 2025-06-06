import os

CS_HOST = "chatsurfer.nro.mil"
TEST = os.environ["TEST_LOCAL"]
CHATKEY = os.environ["CHATKEY"]
BOT_USER_ID = "27fbef28-0663-4659-b479-ca8cd555e013"
CS_WEBSOCKET_URL = f"wss://{CS_HOST}/ws/connect/topic/chat-messages-all/websocket"


if TEST == "True":
    CERT_PATH = "/Users/samueltownsend/dev/certs/justcert.pem"
    KEY_PATH = "/Users/samueltownsend/dev/certs/decrypted.key"
    CA_BUNDLE_PATH = "/Users/samueltownsend/dev/certs/dod_CAs.pem"

else:
    CERT_PATH = "/root/certs/justcert.pem"
    KEY_PATH = "/root/certs/decrypted.key"
    CA_BUNDLE_PATH = "/root/certs/dod_CAs.pem"
