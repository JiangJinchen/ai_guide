import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.utils.streaming import IntentStreamFilter
from app.utils.validation import normalize_entity_id

try:
    from app.api.visitor import (
        intent_to_service_actions,
        normalize_reply_text,
        resolve_stream_service_actions,
    )
except ModuleNotFoundError as import_error:
    if import_error.name != "fastapi":
        raise
    intent_to_service_actions = None
    normalize_reply_text = None
    resolve_stream_service_actions = None


class IntentStreamFilterTests(unittest.TestCase):
    def filter_chunks(self, chunks):
        stream_filter = IntentStreamFilter()
        output = "".join(stream_filter.feed(chunk) for chunk in chunks)
        return output + stream_filter.finish()

    def test_filters_intent_at_every_two_chunk_boundary(self):
        source = '欢迎使用<intent>{"service":"ticket","params":{}}</intent>'
        for split_index in range(len(source) + 1):
            with self.subTest(split_index=split_index):
                self.assertEqual(
                    self.filter_chunks([source[:split_index], source[split_index:]]),
                    "欢迎使用",
                )

    def test_filters_intent_split_one_character_at_a_time(self):
        source = '正文<intent>{"service":"guide"}</intent>结尾'
        self.assertEqual(self.filter_chunks(list(source)), "正文结尾")

    def test_preserves_plain_text(self):
        self.assertEqual(self.filter_chunks(["灵山", "大佛介绍"]), "灵山大佛介绍")

    def test_drops_unterminated_intent_block(self):
        self.assertEqual(self.filter_chunks(["正文<int", "ent>{"]), "正文")


class EntityIdValidationTests(unittest.TestCase):
    def test_accepts_positive_integer_and_numeric_string(self):
        self.assertEqual(normalize_entity_id(12), 12)
        self.assertEqual(normalize_entity_id(" 12 "), 12)

    def test_rejects_model_generated_slug_and_boolean(self):
        self.assertIsNone(normalize_entity_id("ling Shan_da_fo"))
        self.assertIsNone(normalize_entity_id(True))


@unittest.skipIf(intent_to_service_actions is None, "fastapi is not installed")
class ServiceActionTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.query = self.db.query.return_value
        self.query.filter.return_value = self.query

    def test_ticket_intent_uses_existing_ticket_page(self):
        self.query.first.return_value = None
        actions = intent_to_service_actions({"service": "ticket", "params": {}}, self.db)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["path"], "/pages/ticket-assistant/index")
        self.assertEqual(actions[0]["action_type"], "navigate_to")

    def test_navigation_resolves_spot_name_to_location(self):
        self.query.first.return_value = SimpleNamespace(
            id=1,
            spot_name="灵山大佛",
            latitude=31.43,
            longitude=120.1,
            location="灵山胜境",
        )
        actions = intent_to_service_actions(
            {"service": "navigation", "params": {"spot": "灵山大佛"}},
            self.db,
        )

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action_type"], "open_location")
        self.assertEqual(actions[0]["payload"]["name"], "灵山大佛")
        self.assertEqual(actions[0]["payload"]["latitude"], 31.43)

    def test_navigation_without_location_opens_navigation_page(self):
        self.query.first.return_value = None
        actions = intent_to_service_actions(
            {"service": "navigation", "params": {}},
            self.db,
        )

        self.assertEqual(actions[0]["action_type"], "navigate_to")
        self.assertEqual(actions[0]["path"], "/pages/route-navigation/index")

    def test_navigation_request_merges_navigation_and_guide_actions(self):
        spot = SimpleNamespace(
            id=5,
            spot_name="拈花广场",
            latitude=31.42876,
            longitude=120.10242,
            location="灵山胜境",
        )
        self.query.first.return_value = spot
        self.query.all.return_value = [spot]

        actions = resolve_stream_service_actions(
            "我想去拈花广场看看",
            {"service": "guide", "params": {"spot_id": 5}},
            self.db,
        )

        self.assertEqual([action["action_type"] for action in actions], ["open_location", "navigate_to"])
        self.assertEqual(actions[0]["payload"]["name"], "拈花广场")
        self.assertEqual(actions[1]["path"], "/pages/guide/index")

    def test_stream_speech_text_can_keep_full_reply(self):
        text = "完整口播。" * 100
        self.assertEqual(normalize_reply_text(text, max_chars=None), text.rstrip("。"))

    def test_unknown_intent_has_no_action(self):
        self.assertEqual(intent_to_service_actions({"service": "unknown"}, self.db), [])

    def test_non_numeric_model_spot_id_is_not_queried_as_integer_id(self):
        actions = intent_to_service_actions(
            {"service": "guide", "params": {"spot_id": "ling Shan_da_fo"}},
            self.db,
        )

        self.db.query.assert_not_called()
        self.assertNotIn("spot_id", actions[0]["params"])
        self.assertIsNone(normalize_entity_id("ling Shan_da_fo"))


if __name__ == "__main__":
    unittest.main()
