import json
import unittest
from pathlib import Path
from main import MultiAgentPlanner, SchedulingAgent, Task, TaskDecomposerAgent

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = MultiAgentPlanner()
    def test_sample_plan_has_complete_schedule_and_expected_agents(self):
        sample = json.loads((Path(__file__).parents[1] / "sample_tasks.json").read_text(encoding="utf-8"))
        result = self.planner.plan(sample)
        self.assertEqual(result["total_tasks"], 6)
        self.assertEqual(result["total_effort_hours"], 14)
        self.assertEqual(len(result["schedule"]), 6)
        self.assertEqual(len(result["agents"]), 3)
    def test_schedule_never_places_task_before_dependency(self):
        tasks = [Task("a", "A", 1, 1), Task("b", "B", 1, 5, ("a",)), Task("c", "C", 1, 3)]
        schedule = SchedulingAgent().schedule(tasks)
        positions = {item["id"]: item["order"] for item in schedule}
        self.assertLess(positions["a"], positions["b"])
    def test_ready_tasks_use_priority_then_effort(self):
        tasks = [Task("slow", "Slow", 3, 4), Task("fast", "Fast", 1, 4), Task("urgent", "Urgent", 2, 5)]
        schedule = SchedulingAgent().schedule(tasks)
        self.assertEqual([item["id"] for item in schedule], ["urgent", "fast", "slow"])
    def test_cycle_is_reported(self):
        tasks = [Task("a", "A", 1, 3, ("b",)), Task("b", "B", 1, 3, ("a",))]
        with self.assertRaisesRegex(ValueError, "cycle"):
            SchedulingAgent().schedule(tasks)
    def test_unknown_dependency_is_rejected(self):
        data = {"tasks": [{"id": "a", "title": "A", "depends_on": ["missing"]}]}
        with self.assertRaisesRegex(ValueError, "unknown task"):
            TaskDecomposerAgent().decompose(data)
    def test_invalid_effort_is_rejected(self):
        data = {"tasks": [{"id": "a", "title": "A", "effort_hours": 0}]}
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            TaskDecomposerAgent().decompose(data)
    def test_work_items_are_converted_to_a_linear_plan(self):
        tasks = TaskDecomposerAgent().decompose({"work_items": ["Research", "Build", "Test"]})
        self.assertEqual([task.id for task in tasks], ["task-01", "task-02", "task-03"])
        self.assertEqual(tasks[2].dependencies, ("task-02",))
    def test_long_task_is_flagged_for_review(self):
        result = self.planner.plan({"tasks": [{"id": "long", "title": "Large build", "effort_hours": 5}]})
        self.assertTrue(any("consider splitting" in risk["message"] for risk in result["risks"]))
    def test_dependency_bottleneck_is_flagged(self):
        tasks = [{"id": "root", "title": "Shared foundation", "effort_hours": 1}]
        tasks.extend({"id": f"child{i}", "title": f"Child {i}", "effort_hours": 1, "depends_on": ["root"]} for i in range(3))
        result = self.planner.plan({"tasks": tasks})
        self.assertTrue(any("blocks 3 tasks" in risk["message"] for risk in result["risks"]))

if __name__ == "__main__":
    unittest.main()
