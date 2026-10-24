"""v0.6.50 (#191): modelo do adaptador Bluetooth no Windows."""
import unittest

from mesh_analyzer import ble_pairing


class AdapterModel(unittest.TestCase):
    def test_model_from_device_manager(self):
        calls = []

        class Out:
            stdout = "Intel(R) Wireless Bluetooth(R) | OK | USB\\VID_8087&PID_0026\\5&1\n\n"
        model = ble_pairing._windows_adapter_model(lambda cmd, **k: calls.append(cmd) or Out())
        self.assertEqual(model, "Intel(R) Wireless Bluetooth(R) | OK | USB\\VID_8087&PID_0026\\5&1")
        self.assertIn("Get-PnpDevice -Class Bluetooth", calls[0][-1])

    def test_model_failure_is_empty(self):
        def boom(cmd, **k):
            raise FileNotFoundError("powershell")
        self.assertEqual(ble_pairing._windows_adapter_model(boom), "")


if __name__ == "__main__":
    unittest.main()
