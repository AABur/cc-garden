# test_jsonl_parser.py
import unittest
import jsonl_parser as jp


def _assistant_line(uuid, msg_id, req_id, model="claude-opus-4-8",
                    cr=0, c5=0, c1=0, out=10, inp=5, sidechain=False,
                    skill=None, plugin=None, mcp=None, agent=None, kind=None, err=None):
    return {
        "type": "assistant", "uuid": uuid, "requestId": req_id,
        "sessionId": "s1", "cwd": "/tmp/proj", "timestamp": "2026-06-10T00:00:00Z",
        "isSidechain": sidechain, "sessionKind": kind, "apiErrorStatus": err,
        "attributionSkill": skill, "attributionPlugin": plugin,
        "attributionMcpServer": mcp, "attributionAgent": agent,
        "message": {
            "id": msg_id, "model": model, "role": "assistant", "content": [],
            "usage": {
                "input_tokens": inp, "output_tokens": out,
                "cache_read_input_tokens": cr,
                "cache_creation": {"ephemeral_5m_input_tokens": c5, "ephemeral_1h_input_tokens": c1},
                "cache_creation_input_tokens": c5 + c1, "service_tier": "standard",
            },
        },
    }


class TestParser(unittest.TestCase):
    def test_cache_split(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", c5=100, c1=200))
        self.assertEqual(t.usage.cache_write_5m_tokens, 100)
        self.assertEqual(t.usage.cache_write_1h_tokens, 200)

    def test_attribution_extracted(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", skill="superpowers:brainstorming",
                                          plugin="superpowers", sidechain=True, err="429"))
        self.assertEqual(t.attribution_skill, "superpowers:brainstorming")
        self.assertEqual(t.attribution_plugin, "superpowers")
        self.assertTrue(t.is_sidechain)
        self.assertEqual(t.api_error_status, "429")

    def test_dedup_by_message_and_request_id(self):
        # Same (message.id, requestId) appears twice (resume/branch) -> counted once.
        lines = [_assistant_line("u1", "m1", "r1", out=10),
                 _assistant_line("u2", "m1", "r1", out=10),
                 _assistant_line("u3", "m2", "r2", out=10)]
        sess = jp.build_session_from_records("s1", lines)
        self.assertEqual(sess.total_usage.output_tokens, 20)  # 2 unique, not 3
        self.assertEqual(sess.deduped_turn_count, 2)

    def test_synthetic_model_preserved(self):
        t = jp.parse_turn(_assistant_line("u1", "m1", "r1", model="<synthetic>"))
        self.assertEqual(t.model, "<synthetic>")


if __name__ == "__main__":
    unittest.main()
