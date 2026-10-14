"""Regression tests for PDF, per-source RF telemetry and independent analytics."""
import tempfile
import time
import unittest
from pathlib import Path
from mesh_analyzer.database import Database, now_ms
from mesh_analyzer.analytics import calculate, parse_filters
from mesh_analyzer.reporting import generate


class AnalyticsReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.tmp.name)/"archive.sqlite3")
        self.src=self.db.upsert_source({"name":"Bench VHF","kind":"serial","config":{"port":"COM4"},"enabled":False})["id"]

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def add_packet(self, packet_id, sender, via_mqtt=0, snr=5.2):
        timestamp=now_ms()
        self.db.add_packet({"source_id":self.src,"packet_id":str(packet_id),
            "source_packet_key":f"{self.src}:{sender}:{packet_id}:{timestamp}",
            "timestamp_ms":timestamp,"from_node":sender,"to_node":0xffffffff,
            "port":"TEXT_MESSAGE_APP","channel":0,"rx_snr":snr,"rx_rssi":-82,
            "hop_start":5,"hop_limit":4,"via_mqtt":via_mqtt,"encrypted":0,
            "text_preview":"top secret message not in PDF","raw_json":"{}"})

    def test_empty_report_offline(self):
        data=calculate(self.db,{"period":"24h"})
        self.assertEqual(data["counts"]["observations"],0)
        self.assertIsNone(data["counts"]["confirmed_direct_rf"])
        self.assertIn("não",data["diagnosis"]["noise_floor"].lower())
        pdf=generate(self.db,{"period":"all"})
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf),2500)

    def test_metrics_and_pdf_privacy(self):
        self.db.upsert_node(0x12345678,self.src,long_name="Estacao Radio",battery=18,voltage=3.80)
        self.add_packet(7,0x12345678,0,6.5)
        self.add_packet(8,0x12345678,1,None)
        self.db.add_rf_sample(self.src,0x12345678,now_ms()-5000,rx_good=100,rx_bad=10,channel_util=20)
        self.db.add_rf_sample(self.src,0x12345678,now_ms(),rx_good=200,rx_bad=35,channel_util=35)
        result=calculate(self.db,{"period":"24h"})
        self.assertEqual(result["counts"]["observations"],2)
        self.assertEqual(result["counts"]["mqtt"],1)
        self.assertEqual(result["counts"]["originators"] if "originators" in result["counts"] else result["counts"]["active_originators"],1)
        self.assertAlmostEqual(result["rf_samples"][0]["rx_invalid_percent"],25.0)
        self.assertIsNone(result["rf_samples"][0]["crc_error_percent"])
        self.assertGreater(result["counts"]["critical"],0)
        data=generate(self.db,{"period":"24h","source":self.src})
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertGreater(len(data),5000)
        self.assertNotIn(b"top secret message",data)

    def test_stats_filters_reject_invalid(self):
        with self.assertRaises(ValueError):
            parse_filters({"period":"not-a-period"})
        with self.assertRaises(ValueError):
            parse_filters({"source":"-4"})

    def test_reboot_counter_reset_is_ignored(self):
        self.db.add_rf_sample(self.src,0x11223344,now_ms()-5000,rx_good=100,rx_bad=22)
        self.db.add_rf_sample(self.src,0x11223344,now_ms(),rx_good=5,rx_bad=2)
        rf=calculate(self.db,{"period":"all"})["rf_samples"][0]
        self.assertIsNone(rf["rx_invalid_percent"])


if __name__=="__main__":
    unittest.main()
