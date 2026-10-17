import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import greeks_bridge as gb

HTML = '''<div class="tgme_widget_message" data-post="greekslivenews2/1234">
<a class="tgme_widget_message_date"><time datetime="2026-10-17T04:54:00+00:00"></time></a>
<div class="tgme_widget_message_text">BTC-30OCT26-78000-P</div></div>'''
class BridgeTests(unittest.TestCase):
    def test_html(self):
        rows=gb.parse_html(HTML,"greekslivenews2")
        self.assertEqual(rows[0]["post_id"],1234)
        self.assertEqual(len(rows),1)
    def test_baseline_and_no_false_outage(self):
        def mocked(channel,last_seen):
            return (gb.parse_html(HTML,channel) if channel=="greekslivenews2" else []), {"ok":True,"pages":[]}
        with TemporaryDirectory() as d:
            with patch.object(gb,"html_collect",side_effect=mocked), patch.object(gb,"rss_collect",return_value=([],{"ok":False})):
                gb.collect(Path(d))
            payload=gb.json_read(Path(d)/"latest.json",{})
            self.assertTrue(payload["baseline_only"])
            self.assertEqual(payload["new_post_count"],0)
            self.assertEqual(payload["channels"]["laevitas"]["state"],"reachable_but_freshness_not_established")
if __name__=="__main__":
    unittest.main()
