"""Correlate radio routing ACK/NAK with persisted TX; never infer human reading."""
from .database import now_ms
from .transports import number


class MessageReceipts:
    def __init__(self, db):
        self.db=db

    def observe(self, source_id, packet):
        if not isinstance(packet,dict) or packet.get('viaMqtt') or packet.get('via_mqtt'):
            return
        decoded=packet.get('decoded') or {}
        if not isinstance(decoded,dict) or decoded.get('portnum') not in (5,'ROUTING_APP'):
            return
        routing=decoded.get('routing')
        request=number(decoded.get('requestId',decoded.get('request_id')))
        sender=number(packet.get('from',packet.get('fromId')))
        if not isinstance(routing,dict) or not request or not sender:
            return
        reason=routing.get('errorReason',routing.get('error_reason',0))
        with self.db._lock,self.db._db:
            rows=self.db._db.execute("""SELECT * FROM messages WHERE source_id=? AND packet_id=?
                AND direction='tx' AND state='accepted_by_radio' AND timestamp_ms>=? ORDER BY timestamp_ms DESC LIMIT 1""",
                (source_id,str(request),now_ms()-180000)).fetchall()
            for row in rows:
                own=row['from_node']; target=row['to_node']
                if sender!=own and sender!=target and target not in (None,0xffffffff):
                    continue
                if reason not in (0,'NONE'):
                    # Only the local radio or intended recipient can reject TX.
                    if sender!=own and sender!=target:continue
                    state='failed'
                else:
                    # Local implicit ACK signals a rebroadcast, not read/delivery.
                    state='delivered' if target not in (None,0xffffffff) and sender==target else 'mesh_propagated'
                self.db._db.execute('UPDATE messages SET state=? WHERE id=? AND state=?',
                    (state,row['id'],'accepted_by_radio'))

    def expire(self):
        with self.db._lock,self.db._db:
            self.db._db.execute("""UPDATE messages SET state='failed' WHERE direction='tx'
                AND state='accepted_by_radio' AND timestamp_ms<?""",(now_ms()-180000,))
