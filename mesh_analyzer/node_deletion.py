"""Delete a NodeDB entry on the connected local radio before deleting its catalog row.

Historical packets/messages/positions/topology remain intact. A fresh reception can
rediscover the node. No command is addressed to the remote node being removed.
"""
import threading
import time
from .transports import number


class NodeDeletion:
    def __init__(self, manager):
        self.manager = manager
        self._operation = threading.Lock()

    @staticmethod
    def own_number(iface):
        info = getattr(iface, 'myInfo', None)
        return number(info.get('my_node_num', info.get('myNodeNum')) if isinstance(info, dict)
                      else getattr(info, 'my_node_num', None)) or number(getattr(getattr(iface, 'localNode', None), 'nodeNum', None))

    def delete(self, source_id, target, confirmed=False, timeout=30):
        if confirmed is not True:
            raise ValueError('Confirme a exclusão do nó no rádio e no banco')
        target = number(target)
        if target is None or not 4 <= target < 0xffffffff:
            raise ValueError('Node ID inválido ou reservado')
        source_id = int(source_id)
        source = self.manager.db.source(source_id)
        if not source or source['kind'] not in ('serial', 'ble', 'tcp') or not source.get('enabled'):
            raise ValueError('Selecione uma conexão direta ativa com o rádio')
        with self.manager._lock:
            iface = self.manager._interfaces.get(source_id)
            state = self.manager._states.get(source_id, {})
            if iface is None or state.get('status') != 'connected':
                raise ValueError('Rádio desconectado; banco preservado')
            if getattr(iface, 'is_meshcore', False):
                raise ValueError('Apagar nós no rádio MeshCore ainda não é suportado; use o app do MeshCore')
            if any(self.own_number(v) == target for v in self.manager._interfaces.values()):
                raise ValueError('Não é permitido apagar o próprio rádio')
        own = self.own_number(iface)
        local = getattr(iface, 'localNode', None)
        if own is None or number(getattr(local, 'nodeNum', None)) != own:
            raise ValueError('Identidade do rádio local não confirmada')
        if not callable(getattr(local, 'removeNode', None)) or not callable(getattr(local, '_sendAdmin', None)):
            raise ValueError('SDK sem suporte à exclusão confirmada de nó')
        if not self._operation.acquire(blocking=False):
            raise ValueError('Já existe uma exclusão em andamento. Aguarde a conclusão.')
        try:
            return self._delete(iface, local, source_id, target, own, timeout)
        finally:
            self._operation.release()

    def _delete(self, iface, local, source_id, target, own, timeout):
        from meshtastic.protobuf import admin_pb2
        command = admin_pb2.AdminMessage()
        if 'remove_by_nodenum' not in command.DESCRIPTOR.fields_by_name:
            raise ValueError('Protocolo sem suporte à exclusão de nó')
        command.remove_by_nodenum = target
        # Same protocol/session setup as Node.removeNode, with a correlated
        # response handler registered by the SDK BEFORE transmitting.
        local.ensureSessionKey()
        event = threading.Event()
        replies = []
        def onAckNak(packet):
            if not isinstance(packet, dict):
                return
            decoded = packet.get('decoded') or {}
            if not isinstance(decoded, dict):
                return
            routing = decoded.get('routing')
            port = decoded.get('portnum')
            if port not in (5, 'ROUTING_APP') or not isinstance(routing, dict):
                return
            if number(packet.get('from', packet.get('fromId'))) != own:
                return
            replies.append(packet)
            event.set()
        self.manager.db.log(f'Exclusão solicitada: !{target:08x} no NodeDB do rádio !{own:08x}', source_id=source_id)
        packet = local._sendAdmin(command, wantResponse=True, onResponse=onAckNak)
        packet_id = number(packet.get('id') if isinstance(packet, dict) else getattr(packet, 'id', None))
        if not packet_id:
            raise ValueError('Rádio não retornou ID do comando; banco preservado')
        deadline = time.monotonic() + timeout
        ack = None
        while time.monotonic() < deadline:
            with self.manager._lock:
                if self.manager._interfaces.get(source_id) is not iface or self.manager._states.get(source_id, {}).get('status') != 'connected':
                    raise ValueError('Conexão mudou durante a exclusão; banco preservado. Confira o rádio.')
            event.wait(min(.1, max(0, deadline-time.monotonic())))
            event.clear()
            while replies:
                reply = replies.pop(0)
                decoded = reply['decoded']
                if number(decoded.get('requestId', decoded.get('request_id'))) != packet_id:
                    continue
                reason = decoded['routing'].get('errorReason', decoded['routing'].get('error_reason', 0))
                if reason not in (0, 'NONE'):
                    raise ValueError('Rádio rejeitou a exclusão: '+str(reason)+'. Banco preservado.')
                ack = reply
                break
            if ack is not None:
                break
        if ack is None:
            self.manager.db.log(f'Exclusão sem confirmação em 30 s: !{target:08x}; cadastro local preservado', 'warning', source_id)
            raise ValueError('Sem confirmação do rádio em 30 s; banco preservado. O nó pode ter sido removido no rádio.')
        # Cache eviction follows radio confirmation; it is never used as proof.
        with self.manager._lock:
            if self.manager._interfaces.get(source_id) is not iface:
                raise ValueError('Rádio confirmou, mas conexão mudou; cadastro local preservado para reconciliação')
            cache = getattr(iface, 'nodesByNum', None)
            if isinstance(cache, dict):
                cache.pop(target, None)
                cache.pop(str(target), None)
            cache = getattr(iface, 'nodes', None)
            if isinstance(cache, dict):
                cache.pop(f'!{target:08x}', None)
            try:
                removed = self.manager.db.delete_node_catalog(target)
            except Exception as exc:
                self.manager.db.log(f'Exclusão parcial: rádio confirmou !{target:08x}, banco falhou', 'error', source_id)
                raise ValueError('Rádio confirmou a remoção, mas o banco falhou. Tente novamente para reconciliar.') from exc
        self.manager.db.log(f'Exclusão confirmada pelo rádio e cadastro local removido: !{target:08x}', source_id=source_id)
        return {'success':True, 'node_num':target, 'radio_confirmed':True,
                'local_removed':removed, 'history_preserved':True}
