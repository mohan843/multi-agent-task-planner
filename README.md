# Multi-Agent Task Planner

A dependency-free Python mini-project that coordinates three small planning agents to turn a project brief into an ordered schedule and a concise risk review. It demonstrates agent-style role separation without an external model API, so it runs locally and produces repeatable results.

## Agents

- **TaskDecomposerAgent** validates task definitions or converts a list of work items into a simple sequential task breakdown.
- **SchedulingAgent** uses topological sorting to honor dependencies, then ranks currently available tasks by priority and effort. It assigns cumulative estimated hours.
- **RiskReviewAgent** highlights long tasks and dependency bottlenecks for a human to review.
- **MultiAgentPlanner** coordinates the agents and returns a JSON-compatible plan.

## Requirements

- Python 3.9 or newer
- No third-party packages

## Setup

```bash
git clone https://github.com/mohan843/multi-agent-task-planner.git
cd multi-agent-task-planner
python -m venv .venv
# Activate the environment if desired; there are no external packages to install.
```

## Usage

Run the included example:

```bash
python main.py
```

Print machine-readable JSON:

```bash
python main.py --input sample_tasks.json --json
```

Create your own JSON file with an `objective` and either a `tasks` list or a `work_items` list. Each task has an `id`, `title`, optional `effort_hours` (default `1`), optional `priority` from 1 to 5 (default `3`), and optional `depends_on` list of task IDs. Example:

```json
{
  "objective": "Ship a demo",
  "tasks": [
    {"id": "research", "title": "Research options", "effort_hours": 2, "priority": 4, "depends_on": []},
    {"id": "prototype", "title": "Build prototype", "effort_hours": 3, "priority": 5, "depends_on": ["research"]}
  ]
}
```

The planner rejects duplicate IDs, unknown/self dependencies, invalid priorities or effort values, and dependency cycles rather than returning a misleading schedule.

## Tests

Run the standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The sample project plan is in [`sample_tasks.json`](sample_tasks.json).
