"""v0.6.59: detecção automática USB não abre portas de rádios com CAT (PTT acionado)."""
import unittest
from types import SimpleNamespace
import unittest.mock
from unittest.mock import patch

from mesh_analyzer import device_detection as dd


def port(device, vid, pid, description="", manufacturer="", product=""):
    return SimpleNamespace(device=device, vid=vid, pid=pid, description=description, manufacturer=manufacturer,
                           product=product, interface=None)


BOARDS = [port("COM6", 0x10C4, 0xEA60, "Silicon Labs CP210x USB to UART Bridge (COM6)"),   # Heltec Wireless Paper/V2
          port("COM7", 0x303A, 0x1001, "USB Serial Device (COM7)"),                         # ESP32-S3 nativo
          port("COM8", 0x1A86, 0x55D4, "USB-Enhanced-SERIAL CH9102 (COM8)"),                 # Heltec V3/T-Beam
          port("COM9", 0x239A, 0x8029, "RAK4631"),
          port("/dev/ttyACM0", 0x2886, 0x8057, "Wio Tracker")]
RADIOS = [port("COM3", 0x10C4, 0xEA60, "IC-7300", "Silicon Labs", "IC-7300"),               # Icom: CP2102 igual
          port("COM4", 0x10C4, 0xEA70, "Silicon Labs Dual CP2105 USB to UART Bridge: Enhanced COM Port"),  # Yaesu
          port("COM5", 0x0403, 0x6001, "USB Serial Port"),                                  # FTDI (cabo CAT/TNC)
          port("COM10", 0x067B, 0x2303, "Prolific USB-to-Serial Comm Port"),
          port("COM11", 0x1A86, 0x7523, "USB-SERIAL CH340 (Kenwood TS-590 CAT)"),
          port("COM13", 0x1A86, 0x7523, "USB-SERIAL CH340 (COM13)"),   # cabo CAT genérico (diagnóstico PU2MUS)
          port("COM12", 0x08BB, 0x2904, "USB Audio CODEC"),
          port("COM1", None, None, "Porta de comunicação")]


class AutoDetectPorts(unittest.TestCase):
    def test_only_mesh_boards_are_opened_automatically(self):
        with patch("serial.tools.list_ports.comports", return_value=BOARDS + RADIOS):
            found = [p["address"] for p in dd.usb_serial_ports()]
        self.assertEqual(found, [p.device for p in BOARDS])

    def test_communication_words_do_not_hide_boards(self):
        self.assertTrue(dd.board_port(port("COM6", 0x10C4, 0xEA60, "CP2102 USB to UART Bridge Controller - communication")))



class SerialFallback(unittest.TestCase):
    """Placa MeshCore cadastrada como Meshtastic (formulário padrão) passa a conectar."""

    def run_open(self, meshcore_ok=True):
        from mesh_analyzer import transports, meshcore_driver
        fake = SimpleNamespace(_stop=SimpleNamespace(is_set=lambda: False), db=unittest.mock.Mock(),
                               _on_packet=None, _lost=None, _on_meshcore_event=None)

        def meshtastic(**kw):
            raise RuntimeError("Timed out waiting for connection completion")

        def meshcore(*a, **kw):
            if not meshcore_ok:
                raise RuntimeError("O rádio MeshCore não respondeu a tempo")
            return "MC"
        with patch("meshtastic.serial_interface.SerialInterface", side_effect=meshtastic), \
                patch.object(meshcore_driver, "MeshCoreInterface", side_effect=meshcore):
            return fake, transports.SourceManager._open_serial(fake, 2, {"name": "COM6"}, {"port": "COM6", "protocol": "meshtastic"})

    def test_meshcore_board_is_switched_to_meshcore(self):
        fake, iface = self.run_open()
        self.assertEqual(iface, "MC")
        fake.db.upsert_source.assert_called_once_with({"id": 2, "config": {"protocol": "meshcore"}})

    def test_original_error_when_neither_answers(self):
        with self.assertRaisesRegex(RuntimeError, "Timed out"):
            self.run_open(meshcore_ok=False)


if __name__ == "__main__":
    unittest.main()
