import paho.mqtt.client as mqtt


class QueueSubscribe:

    def __init__(self, device_id: str ):
        self.device_id = device_id
        self.username = "edge_admin"
        self.password = "Q2JNzkZh.K8@_ee"

        self.broker = "e0cce88517644183b5332d1aabbee868.s1.eu.hivemq.cloud"
        self.port = 8883
        self.client = mqtt.Client(
            client_id=self.device_id,
            clean_session=False
        )

    def connect(self, on_connect, on_message):

        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set()

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        print("🚀 Connecting to HiveMQ Cloud...")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_forever()



