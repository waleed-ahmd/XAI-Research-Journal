from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from harness.batch import (
    build_anthropic_batch_requests,
    build_openai_batch_jsonl,
    collect_anthropic_batch,
    collect_openai_batch,
    pending_batch_keys,
)
from harness.data.models import SelectedQuestion
from harness.runner import build_plan
from harness.data.loader import load_all_questions


def _plan(small_config, fixture_data_dir):
    selected = [
        SelectedQuestion(index=0, task="fake_task_a", idx=0, num_choices=4, gold_letter="A", cued_letter="B")
    ]
    questions = {q.question_id: q for q in load_all_questions(small_config.questions.tasks, fixture_data_dir)}
    return build_plan(selected, questions, small_config, "openai")


def test_openai_batch_jsonl_matches_responses_request(small_config, fixture_data_dir):
    plan = _plan(small_config, fixture_data_dir)
    payload = build_openai_batch_jsonl(plan, small_config.models.openai)
    row = json.loads(payload.splitlines()[0])
    assert row["custom_id"] == plan[0].key
    assert row["method"] == "POST"
    assert row["url"] == "/v1/responses"
    assert row["body"]["model"] == "fake-gpt"
    assert row["body"]["reasoning"]["effort"] == "medium"


def test_anthropic_batch_requests_match_messages_request(small_config, fixture_data_dir):
    plan = _plan(small_config, fixture_data_dir)
    requests = build_anthropic_batch_requests(plan, small_config.models.anthropic)
    assert requests[0]["custom_id"] == plan[0].key
    assert requests[0]["params"]["model"] == "fake-claude"
    assert requests[0]["params"]["output_config"]["effort"] == "high"


def test_pending_batch_keys_ignores_collected_and_failed(tmp_path):
    batch_dir = tmp_path / "batches"
    batch_dir.mkdir()
    active = {
        "status": "in_progress",
        "calls": [{"key": "active-key"}],
    }
    collected = {
        "status": "completed",
        "collected_at": "2026-10-20T00:00:00+00:00",
        "calls": [{"key": "collected-key"}],
    }
    failed = {
        "status": "failed",
        "calls": [{"key": "failed-key"}],
    }
    (batch_dir / "openai-a.json").write_text(json.dumps(active))
    (batch_dir / "openai-b.json").write_text(json.dumps(collected))
    (batch_dir / "openai-c.json").write_text(json.dumps(failed))
    assert pending_batch_keys(batch_dir, "openai") == {"active-key"}


def test_collect_openai_batch_writes_normal_result(tmp_path, small_config):
    key = "a" * 64
    manifest_path = tmp_path / "batches" / "openai-batch.json"
    manifest_path.parent.mkdir()
    results_path = tmp_path / "raw" / "openai.jsonl"
    manifest = {
        "schema_version": 1,
        "provider": "openai",
        "model_name": "openai",
        "model_id": "fake-gpt",
        "batch_id": "batch_1",
        "status": "completed",
        "manifest_path": str(manifest_path),
        "results_path": str(results_path),
        "request_count": 1,
        "calls": [{
            "key": key,
            "question_id": "fake_task_a:0",
            "task": "fake_task_a",
            "idx": 0,
            "condition": "original",
            "model_name": "openai",
            "run_index": 0,
            "gold_letter": "A",
            "cued_letter": "B",
            "prompt": "question",
            "request_params": {"model": "fake-gpt", "input": "question"},
        }],
    }
    manifest_path.write_text(json.dumps(manifest))

    class Files:
        def content(self, file_id):
            return SimpleNamespace(text=json.dumps({
                "custom_id": key,
                "response": {
                    "status_code": 200,
                    "body": {
                        "model": "fake-gpt",
                        "output": [{
                            "type": "message",
                            "content": [{"type": "output_text", "text": "The best answer is: (A)"}],
                        }],
                    },
                },
                "error": None,
            }))

    class Batches:
        def retrieve(self, batch_id):
            return SimpleNamespace(status="completed", output_file_id="file_1", error_file_id=None)

    client = SimpleNamespace(files=Files(), batches=Batches())
    summary = collect_openai_batch(manifest, client=client)
    assert summary["collected"] == 1
    row = json.loads(results_path.read_text().splitlines()[0])
    assert row["key"] == key
    assert row["answer_text"] == "The best answer is: (A)"
    assert row["batch_id"] == "batch_1"


def test_collect_anthropic_batch_writes_normal_result(tmp_path):
    key = "b" * 64
    manifest_path = tmp_path / "batches" / "anthropic-batch.json"
    manifest_path.parent.mkdir()
    results_path = tmp_path / "raw" / "anthropic.jsonl"
    manifest = {
        "schema_version": 1,
        "provider": "anthropic",
        "model_name": "anthropic",
        "model_id": "fake-claude",
        "batch_id": "msgbatch_1",
        "status": "ended",
        "manifest_path": str(manifest_path),
        "results_path": str(results_path),
        "request_count": 1,
        "calls": [{
            "key": key,
            "question_id": "fake_task_a:0",
            "task": "fake_task_a",
            "idx": 0,
            "condition": "original",
            "model_name": "anthropic",
            "run_index": 0,
            "gold_letter": "A",
            "cued_letter": "B",
            "prompt": "question",
            "request_params": {"model": "fake-claude", "messages": [{"role": "user", "content": "question"}]},
        }],
    }
    manifest_path.write_text(json.dumps(manifest))

    class Batches:
        def retrieve(self, batch_id):
            return SimpleNamespace(processing_status="ended")

        def results(self, batch_id):
            return iter([
                SimpleNamespace(model_dump=lambda: {
                    "custom_id": key,
                    "result": {
                        "type": "succeeded",
                        "message": {
                            "model": "fake-claude",
                            "content": [{"type": "text", "text": "The best answer is: (A)"}],
                        },
                    },
                })
            ])

    client = SimpleNamespace(messages=SimpleNamespace(batches=Batches()))
    summary = collect_anthropic_batch(manifest, client=client)
    assert summary["collected"] == 1
    row = json.loads(results_path.read_text().splitlines()[0])
    assert row["key"] == key
    assert row["answer_text"] == "The best answer is: (A)"
    assert row["batch_id"] == "msgbatch_1"
