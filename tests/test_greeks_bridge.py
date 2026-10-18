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
    def test_delayed_job_preserves_new_messages(self):
        with TemporaryDirectory() as d:
            old={"key":"greekslivenews2/1233","channel":"greekslivenews2",
                 "post_id":1233,"utc":"2026-10-17T01:00:00+00:00",
                 "text":"previous","source":"public_html"}
            gb.json_write(Path(d)/"messages.json",[old])
            def mocked(channel,last_seen):
                self.assertEqual(last_seen,1233 if channel=="greekslivenews2" else None)
                return (gb.parse_html(HTML,channel) if channel=="greekslivenews2" else []), {"ok":True,"pages":[]}
            with patch.object(gb,"utcnow",return_value=datetime(2026,10,17,9,0,tzinfo=timezone.utc)), patch.object(gb,"html_collect",side_effect=mocked), patch.object(gb,"rss_collect",return_value=([],{"ok":False})):
                gb.collect(Path(d))
            payload=gb.json_read(Path(d)/"latest.json",{})
            self.assertFalse(payload["baseline_only"])
            self.assertEqual(payload["new_post_count"],1)
            self.assertEqual(payload["new_posts"][0]["key"],"greekslivenews2/1234")
    def test_old_unseen_id_not_realerted(self):
        with TemporaryDirectory() as d:
            old={"key":"greekslivenews2/1235","channel":"greekslivenews2",
                 "post_id":1235,"utc":"2026-10-17T06:00:00+00:00",
                 "text":"already collected newer post","source":"public_html"}
            gb.json_write(Path(d)/"messages.json",[old])
            def mocked(channel,last_seen):
                return (gb.parse_html(HTML,channel) if channel=="greekslivenews2" else []), {"ok":True,"pages":[]}
            with patch.object(gb,"utcnow",return_value=datetime(2026,10,17,9,0,tzinfo=timezone.utc)), patch.object(gb,"html_collect",side_effect=mocked), patch.object(gb,"rss_collect",return_value=([],{"ok":False})):
                gb.collect(Path(d))
            payload=gb.json_read(Path(d)/"latest.json",{})
            self.assertEqual(payload["new_post_count"],0)
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
