"""A small, dependency-free multi-agent task planning demo."""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Task:
    """A task in the project dependency graph."""
    id: str
    title: str
    effort_hours: float
    priority: int = 3
    dependencies: tuple[str, ...] = ()

class TaskDecomposerAgent:
    """Turns a high-level work-item list into a dependency-aware task graph."""
    def decompose(self, plan_input: dict[str, Any]) -> list[Task]:
        raw_tasks = plan_input.get("tasks")
        if raw_tasks is None:
            work_items = plan_input.get("work_items")
            if not isinstance(work_items, list) or not work_items:
                raise ValueError("Provide a non-empty 'tasks' or 'work_items' list.")
            raw_tasks = [
                {"id": f"task-{index:02d}", "title": str(item), "effort_hours": 1.0, "priority": 3, "depends_on": [f"task-{index - 1:02d}"] if index > 1 else []}
                for index, item in enumerate(work_items, start=1)
            ]
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ValueError("'tasks' must be a non-empty list.")
        tasks: list[Task] = []
        seen: set[str] = set()
        for row in raw_tasks:
            if not isinstance(row, dict):
                raise ValueError("Each task must be an object.")
            task_id = str(row.get("id", "")).strip()
            title = str(row.get("title", "")).strip()
            if not task_id or not title:
                raise ValueError("Every task needs a non-empty id and title.")
            if task_id in seen:
                raise ValueError(f"Duplicate task id: {task_id}")
            seen.add(task_id)
            try:
                effort = float(row.get("effort_hours", 1))
                priority = int(row.get("priority", 3))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid effort or priority for task {task_id}.") from exc
            if effort <= 0:
                raise ValueError(f"Task {task_id} effort_hours must be greater than zero.")
            if not 1 <= priority <= 5:
                raise ValueError(f"Task {task_id} priority must be between 1 and 5.")
            dependencies = row.get("depends_on", [])
            if not isinstance(dependencies, list):
                raise ValueError(f"Task {task_id} depends_on must be a list.")
            tasks.append(Task(task_id, title, effort, priority, tuple(map(str, dependencies))))
        ids = {task.id for task in tasks}
        for task in tasks:
            missing = set(task.dependencies) - ids
            if missing:
                raise ValueError(f"Task {task.id} depends on unknown task(s): {', '.join(sorted(missing))}")
            if task.id in task.dependencies:
                raise ValueError(f"Task {task.id} cannot depend on itself.")
        return tasks

class SchedulingAgent:
    """Produces a deterministic, sequential schedule that honors dependencies."""
    def schedule(self, tasks: list[Task]) -> list[dict[str, Any]]:
        by_id = {task.id: task for task in tasks}
        dependents: dict[str, set[str]] = {task.id: set() for task in tasks}
        remaining = {task.id: set(task.dependencies) for task in tasks}
        for task in tasks:
            for dependency in task.dependencies:
                dependents[dependency].add(task.id)
        ready = {task_id for task_id, dependencies in remaining.items() if not dependencies}
        ordered: list[Task] = []
        while ready:
            selected_id = min(ready, key=lambda task_id: (-by_id[task_id].priority, by_id[task_id].effort_hours, task_id))
            ready.remove(selected_id)
            ordered.append(by_id[selected_id])
            for child in dependents[selected_id]:
                remaining[child].discard(selected_id)
                if not remaining[child]:
                    ready.add(child)
        if len(ordered) != len(tasks):
            cyclic = sorted(task_id for task_id, dependencies in remaining.items() if dependencies)
            raise ValueError(f"Dependency cycle detected involving: {', '.join(cyclic)}")
        schedule: list[dict[str, Any]] = []
        cursor = 0.0
        for position, task in enumerate(ordered, start=1):
            end = cursor + task.effort_hours
            schedule.append({"order": position, "id": task.id, "title": task.title, "priority": task.priority, "effort_hours": task.effort_hours, "start_hour": round(cursor, 2), "end_hour": round(end, 2), "depends_on": list(task.dependencies)})
            cursor = end
        return schedule

class RiskReviewAgent:
    """Flags long tasks and dependency bottlenecks for human review."""
    def review(self, tasks: list[Task]) -> list[dict[str, str]]:
        child_count = {task.id: 0 for task in tasks}
        for task in tasks:
            for dependency in task.dependencies:
                child_count[dependency] += 1
        risks: list[dict[str, str]] = []
        for task in tasks:
            if task.effort_hours >= 5:
                risks.append({"level": "medium", "task_id": task.id, "message": f"'{task.title}' is a long task ({task.effort_hours:g}h); consider splitting it."})
            if child_count[task.id] >= 3:
                risks.append({"level": "high", "task_id": task.id, "message": f"'{task.title}' blocks {child_count[task.id]} tasks and may become a bottleneck."})
        if not risks:
            risks.append({"level": "low", "task_id": "", "message": "No major risks detected by the rule-based reviewer."})
        return risks

class MultiAgentPlanner:
    """Coordinates decomposition, scheduling, and risk-review agents."""
    def __init__(self) -> None:
        self.decomposer = TaskDecomposerAgent()
        self.scheduler = SchedulingAgent()
        self.risk_reviewer = RiskReviewAgent()
    def plan(self, plan_input: dict[str, Any]) -> dict[str, Any]:
        objective = str(plan_input.get("objective", "Untitled project")).strip() or "Untitled project"
        tasks = self.decomposer.decompose(plan_input)
        schedule = self.scheduler.schedule(tasks)
        risks = self.risk_reviewer.review(tasks)
        return {"objective": objective, "agents": ["TaskDecomposerAgent", "SchedulingAgent", "RiskReviewAgent"], "total_tasks": len(tasks), "total_effort_hours": round(sum(task.effort_hours for task in tasks), 2), "schedule": schedule, "risks": risks}

def render_report(result: dict[str, Any]) -> str:
    lines = [f"Objective: {result['objective']}", f"Estimated effort: {result['total_effort_hours']:g} hours", "", "Plan:"]
    for task in result["schedule"]:
        lines.append(f"{task['order']:>2}. [{task['id']}] {task['title']} ({task['effort_hours']:g}h, priority {task['priority']}) hours {task['start_hour']:g}-{task['end_hour']:g}")
    lines.append("\nRisk review:")
    for risk in result["risks"]:
        lines.append(f"- [{risk['level'].upper()}] {risk['message']}")
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Create a dependency-aware plan with three cooperating agents.")
    parser.add_argument("--input", default="sample_tasks.json", help="Path to a project plan JSON file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a report")
    args = parser.parse_args()
    try:
        plan_input = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = MultiAgentPlanner().plan(plan_input)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps(result, indent=2) if args.json else render_report(result))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
