"""Roles advertised by Meshtastic User messages, without guessing from names."""
import base64
import re

ROLES=('CLIENT','CLIENT_MUTE','ROUTER','ROUTER_CLIENT','REPEATER','TRACKER',
       'SENSOR','TAK','CLIENT_HIDDEN','LOST_AND_FOUND','TAK_TRACKER','ROUTER_LATE','CLIENT_BASE')


def normalize_role(value):
    if isinstance(value,bool) or value is None:return None
    if isinstance(value,int) or isinstance(value,str) and value.strip().isdigit():
        num=int(value)
        return ROLES[num] if 0<=num<len(ROLES) else None
    if not isinstance(value,str):return None
    name=re.sub(r'[\s-]+','_',value.strip().upper())
    return name if name in ROLES else None


def decoded_user(decoded):
    """Read dictionary and protobuf User; proto role zero is genuinely CLIENT."""
    user=decoded.get('user')
    if not isinstance(user,dict):
        info=decoded.get('nodeInfo') or decoded.get('node_info') or {}
        user=info.get('user') if isinstance(info,dict) else None
    result=dict(user) if isinstance(user,dict) else {}
    payload=decoded.get('payload')
    if isinstance(payload,dict):payload=payload.get('base64')
    try:
        if isinstance(payload,str):payload=base64.b64decode(payload,validate=True)
        if isinstance(payload,(bytes,bytearray)) and payload:
            from meshtastic.protobuf import mesh_pb2
            from google.protobuf.json_format import MessageToDict
            message=mesh_pb2.User();message.ParseFromString(bytes(payload))
            # Reject unknown-only/empty protobufs instead of inventing CLIENT.
            if message.ListFields():
                wire=MessageToDict(message)
                wire['role']=int(message.role)
                result={**wire,**result}
    except (ValueError,TypeError,ImportError,base64.binascii.Error):
        pass
    except Exception:
        # Malformed protobuf must not stop receiving unrelated packets.
        pass
    return result
