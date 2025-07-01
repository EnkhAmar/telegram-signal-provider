from extension import apigw_client
import json


connection_id = "NAp7bdJdIE0CIrg="
apigw_client.get_connection(ConnectionId=connection_id)

apigw_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps({"message": "Hello"}).encode("utf-8"))