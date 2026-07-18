import unittest
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import types
from unittest.mock import Mock, patch

stub_models = types.ModuleType("app.models")
for name in [
    "AppUserBehavior",
    "RouteHistory",
    "ScenicActivity",
    "Spot",
    "TicketProduct",
    "VisitorInteraction",
]:
    setattr(stub_models, name, type(name, (), {}))
stub_models.Spot.id = "id"
stub_models.Spot.scenic_area_name = "scenic_area_name"
sys.modules.setdefault("app.models", stub_models)

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "api" / "dialog_orchestrator.py"
SPEC = importlib.util.spec_from_file_location("dialog_orchestrator_for_test", MODULE_PATH)
dialog_orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dialog_orchestrator)
handle_activities = dialog_orchestrator.handle_activities
handle_general_chat = dialog_orchestrator.handle_general_chat
is_contextual_spot_question = dialog_orchestrator.is_contextual_spot_question
empty_conversation_state = dialog_orchestrator.empty_conversation_state
derive_turn_state = dialog_orchestrator.derive_turn_state
resolve_recent_spot = dialog_orchestrator.resolve_recent_spot
remember = dialog_orchestrator.remember


class ActivityFilteringTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        spot_query = self.db.query.return_value
        spot_query.all.return_value = [
            SimpleNamespace(id=2, spot_name="灵山梵宫"),
            SimpleNamespace(id=3, spot_name="九龙灌浴"),
        ]

    @patch.object(dialog_orchestrator, "activity_items")
    def test_explicit_spot_activity_query_filters_to_matching_spot(self, mock_activity_items):
        mock_activity_items.return_value = [
            {
                "id": -101,
                "name": "九龙灌浴",
                "location": "九龙灌浴广场",
                "schedule_times": ["10:00", "11:30"],
            },
            {
                "id": -102,
                "name": "梵宫吉祥颂",
                "location": "灵山梵宫",
                "schedule_times": ["10:00", "11:00"],
            },
        ]

        result = handle_activities("九龙灌浴演出时间", self.db, {"remaining_today": False, "now": False})

        self.assertTrue(result.handled)
        self.assertIn("九龙灌浴", result.reply_text)
        self.assertNotIn("灵山梵宫", result.reply_text)
        self.assertTrue(result.context["debug_info"]["activity_filter_applied"])

    @patch.object(dialog_orchestrator, "activity_items")
    def test_general_activity_query_keeps_all_performances(self, mock_activity_items):
        mock_activity_items.return_value = [
            {
                "id": -101,
                "name": "九龙灌浴",
                "location": "九龙灌浴广场",
                "schedule_times": ["10:00", "11:30"],
            },
            {
                "id": -102,
                "name": "梵宫吉祥颂",
                "location": "灵山梵宫",
                "schedule_times": ["10:00", "11:00"],
            },
        ]

        result = handle_activities("今天有什么演出", self.db, {"remaining_today": False, "now": False})

        self.assertTrue(result.handled)
        self.assertIn("九龙灌浴", result.reply_text)
        self.assertIn("灵山梵宫", result.reply_text)
        self.assertFalse(result.context["debug_info"]["activity_filter_applied"])


class GeneralChatGuardTests(unittest.TestCase):
    def test_self_intro_is_not_treated_as_contextual_spot_question(self):
        db = Mock()
        query = db.query.return_value
        query.all.return_value = [SimpleNamespace(id=3, spot_name="九龙灌浴")]

        self.assertFalse(is_contextual_spot_question("介绍一下你自己吧", db))

    def test_self_intro_returns_general_chat_response(self):
        result = handle_general_chat("介绍一下你自己吧")

        self.assertTrue(result.handled)
        self.assertIn("灵山胜境数字导游", result.reply_text)
        self.assertEqual(result.context["debug_info"]["matched_intent"], "self_intro")


class ConversationStateTests(unittest.TestCase):
    @patch.object(dialog_orchestrator, "resolve_scenic_area_name")
    @patch.object(dialog_orchestrator, "resolve_spot")
    @patch.object(dialog_orchestrator, "infer_turn_task")
    def test_switching_to_spot_list_resets_previous_spot_anchor(self, mock_task, mock_resolve_spot, mock_resolve_scenic):
        previous_state = empty_conversation_state()
        previous_state.update({
            "current_domain": "五灯湖",
            "current_task": "spot_guide",
            "current_scenic_area": "五灯湖",
            "current_spot_id": 11,
            "current_spot_name": "五灯湖",
        })
        mock_task.return_value = "spot_list"
        mock_resolve_spot.return_value = None
        mock_resolve_scenic.return_value = "灵山胜境"

        next_state = derive_turn_state(
            "灵山胜境的景点有哪些",
            Mock(),
            [],
            {"route": False, "preference": False, "history": False, "nearby": False, "today": False, "remaining_today": False, "now": False},
            previous_state,
        )

        self.assertEqual(next_state["current_task"], "spot_list")
        self.assertEqual(next_state["current_domain"], "灵山胜境")
        self.assertEqual(next_state["current_scenic_area"], "灵山胜境")
        self.assertEqual(next_state["current_spot_name"], "")
        self.assertIsNone(next_state["current_spot_id"])

    def test_route_planning_state_does_not_reuse_old_spot_from_memory(self):
        memory_key = "tester:route-reset"
        remember(memory_key, {
            "conversation_state": {
                "current_domain": "五灯湖",
                "current_task": "spot_guide",
                "current_scenic_area": "五灯湖",
                "current_spot_id": 11,
                "current_spot_name": "五灯湖",
            }
        })

        route_state = empty_conversation_state()
        route_state.update({
            "current_domain": "灵山胜境",
            "current_task": "route_planning",
            "current_scenic_area": "灵山胜境",
        })

        db = Mock()
        self.assertIsNone(resolve_recent_spot(memory_key, db, route_state))
        db.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
