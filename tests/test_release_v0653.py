"""v0.6.53 (#191): no Windows, abre a sessão GATT e espera ficar ativa antes do bleak (como o Chrome)."""
import unittest
from unittest.mock import patch

import meshtastic.ble_interface as mble

from mesh_analyzer import ble_link
from test_release_v0647 import ADDR, Scanner, fake_client_class


class Held:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class Prewarm(unittest.TestCase):
    def run_connect(self, behaviours, active=True, attempts=2):
        created, calls, held = [], [], []

        def prewarm(address, helper):
            calls.append(address)
            held.append(Held())
            return held[-1], active
        with patch.object(mble, "BLEClient", fake_client_class(list(behaviours), created)):
            try:
                client = ble_link.connect_client(ADDR, lambda c: None, attempts=attempts, sleep=lambda s: None,
                                                 bleak=Scanner(), prewarm=prewarm)
                return client, None, calls, held
            except ble_link.LinkError as exc:
                return None, exc, calls, held

    def test_session_is_opened_before_connecting_and_released_after(self):
        client, error, calls, held = self.run_connect(["ok"])
        self.assertIsNone(error)
        self.assertEqual(calls, [ADDR])
        self.assertTrue(held[0].closed)

    def test_session_released_on_each_failed_attempt(self):
        _, error, calls, held = self.run_connect(["unreachable", "unreachable"])
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(h.closed for h in held))
        self.assertNotIn("sessão Bluetooth", str(error))

    def test_inactive_session_is_reported(self):
        _, error, _, _ = self.run_connect(["unreachable"], active=False, attempts=1)
        self.assertIn("a sessão Bluetooth do Windows não ficou ativa em 20 s", str(error))

    def test_prewarm_errors_do_not_block_the_connection(self):
        created = []

        def broken(address, helper):
            raise OSError("WinRT indisponível")
        with patch.object(mble, "BLEClient", fake_client_class(["ok"], created)):
            client = ble_link.connect_client(ADDR, lambda c: None, sleep=lambda s: None, bleak=Scanner(), prewarm=broken)
        self.assertIs(client, created[0])

    def test_only_windows_uses_it_by_default(self):
        for platform, expected in (("linux", 0), ("darwin", 0), ("win32", 1)):
            created, calls = [], []

            def fake(address, helper):
                calls.append(address)
                return Held(), True
            with patch.object(mble, "BLEClient", fake_client_class(["ok"], created)), \
                 patch.object(ble_link, "windows_prewarm", fake), patch.object(ble_link.sys, "platform", platform):
                ble_link.connect_client(ADDR, lambda c: None, sleep=lambda s: None, bleak=Scanner())
            self.assertEqual(len(calls), expected, platform)


if __name__ == "__main__":
    unittest.main()
