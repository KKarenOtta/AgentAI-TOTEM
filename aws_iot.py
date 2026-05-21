import json
import os

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

_client = None


def get_client():
    global _client

    if _client:
        return _client

    client = AWSIoTMQTTClient("totem-virtual")

    client.configureEndpoint(
        os.getenv("AWS_IOT_ENDPOINT"),
        8883,
    )

    client.configureCredentials(
        os.getenv("AWS_IOT_ROOT_CA"),
        os.getenv("AWS_IOT_PRIVATE_KEY"),
        os.getenv("AWS_IOT_CERT"),
    )

    client.connect()

    _client = client
    return client


def publish_event(topic: str, payload: dict):
    try:
        client = get_client()

        client.publish(
            topic,
            json.dumps(payload),
            1,
        )

    except Exception as e:
        print("MQTT ERROR:", e)
