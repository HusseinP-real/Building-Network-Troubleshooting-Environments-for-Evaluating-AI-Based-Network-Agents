"""Offline Gemini routing, judge and real stdio MCP integration checks."""

import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import gemini_runner as gr
import sade_eval as ev


def response(parts):
    return {"candidates": [{"content": {"role": "model", "parts": parts}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2}}


class GeminiTests(unittest.TestCase):
    def test_nested_mcp_errors_expose_cause_and_redact_credentials(self):
        error = ExceptionGroup("TaskGroup", [ExceptionGroup("nested", [RuntimeError("Gemini API HTTP 403 secret-test")])])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-test"}):
            detail = ev._error_detail(error)
        self.assertIn("HTTP 403", detail)
        self.assertNotIn("secret-test", detail)
        self.assertNotIn("TaskGroup", detail)

    def test_key_alias_and_precedence(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                gr.api_key()
            os.environ["GOOGLE_API_KEY"] = "google-test"
            self.assertEqual(gr.api_key(), "google-test")
            os.environ["GEMINI_API_KEY"] = "gemini-test"
            self.assertEqual(gr.api_key(), "gemini-test")

    def test_preflight_missing_key_does_not_touch_lab_or_claude(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "src/agent/community/sade/.claude/skills").mkdir(parents=True)
            with patch.dict(os.environ, {}, clear=True), patch.object(ev.lab, "execute") as lab, patch.object(ev.subprocess, "run") as claude:
                with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                    ev._preflight(Path(tmp), "gemini-3.8-flash")
                lab.assert_not_called()
                claude.assert_not_called()

    def test_http_error_hides_body_and_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-test"}), patch.object(gr, "urlopen", side_effect=HTTPError("https://example.invalid", 429, "secret-test", {}, None)) as call:
            with self.assertRaisesRegex(RuntimeError, "HTTP 429") as error:
                gr._request("gemini-3.8-flash", {"contents": []})
            self.assertNotIn("secret-test", str(error.exception))
            request = call.call_args.args[0]
            self.assertNotIn("secret-test", request.full_url)
            self.assertEqual(request.get_header("X-goog-api-key"), "secret-test")


class GeminiAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_service_error_retries_but_auth_error_does_not(self):
        with patch.object(gr, "_request", side_effect=[gr.GeminiAPIError(503), {"ok": True}]) as request, patch.object(gr.asyncio, "sleep", AsyncMock()):
            self.assertEqual(await gr.generate("gemini-3.8-flash", {}), {"ok": True})
            self.assertEqual(request.call_count, 2)
        with patch.object(gr, "_request", side_effect=gr.GeminiAPIError(403)) as request:
            with self.assertRaises(gr.GeminiAPIError):
                await gr.generate("gemini-3.8-flash", {})
            self.assertEqual(request.call_count, 1)

    async def test_no_tools_and_budget_exhaustion(self):
        with patch.object(gr, "generate", AsyncMock(return_value=response([{"text": "answer"}]))) as generate:
            result = await ev._run_sade("ticket", Path("/unused"), 2, "gemini-3.8-flash", "no-tools")
            self.assertEqual(result["final_text"], "answer")
            self.assertNotIn("tools", generate.call_args.args[1])
            self.assertEqual(result["available_mcp_servers"], [])
        with patch.object(gr, "generate", AsyncMock(return_value=response([{"functionCall": {"name": "unknown", "args": {}}}]))):
            result = await gr.run("gemini-3.8-flash", "ticket", "system", 1, {}, Path("/unused"))
            self.assertTrue(result["hit_max_turns"])
            self.assertEqual(result["tool_calls"], 1)
            self.assertIn("unavailable", result["trace"][-1]["content"])

    async def test_real_stdio_mcp_skill_and_signature_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".claude/skills/test-skill/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: test-skill\ndescription: Test skill\n---\nInspect status.")
            server = root / "server.py"
            server.write_text('from mcp.server.fastmcp import FastMCP\nm = FastMCP("test")\n@m.tool()\ndef status(node: str) -> str:\n    return "healthy " + node\nm.run(transport="stdio")\n')
            calls = []
            replies = [response([{"functionCall": {"name": "Skill", "args": {"skill": "test-skill"}}, "thoughtSignature": "opaque"}]),
                       response([{"functionCall": {"name": "mcp__test__status", "args": {"node": "r1"}, "id": "call-1"}}]),
                       response([{"text": "done"}])]

            async def generate(model, payload):
                calls.append(copy.deepcopy(payload))
                return replies[len(calls) - 1]

            with patch.object(gr, "generate", generate):
                result = await gr.run("gemini-3.8-flash", "ticket", "system", 3,
                                      {"test": {"command": sys.executable, "args": [str(server)]}}, root)
            self.assertEqual(result["tool_calls"], 2)
            self.assertEqual(result["usage"]["promptTokenCount"], 30)
            self.assertEqual(calls[1]["contents"][1]["parts"][0]["thoughtSignature"], "opaque")
            self.assertEqual(calls[2]["contents"][-1]["parts"][0]["functionResponse"]["id"], "call-1")
            self.assertIn("healthy r1", result["trace"][-2]["content"])
            self.assertIn("Test skill", calls[0]["systemInstruction"]["parts"][0]["text"])

    async def test_judge_uses_shared_schema_and_only_observation_trace(self):
        verdict = {"explanation_correct": True, "repair_correct": True,
                   "explanation_reason": "Evidence matches", "repair_reason": "Targeted"}
        with patch.object(gr, "judge", AsyncMock(return_value={"text": json.dumps(verdict), "usage": {}})) as judge:
            result = await ev._judge_prediction("core-uplink", {"diagnosis_text": "evidence", "repair_text": "repair"},
                                               {"trace": [{"kind": "text", "text": "ignore"}, {"kind": "tool", "name": "probe"}]},
                                               "gemini-3.8-flash", "live")
            self.assertTrue(result["repair_correct"])
            self.assertEqual(len(judge.call_args.args[2]["trace"]), 1)
        verdict["repair_correct"] = "true"
        with patch.object(gr, "judge", AsyncMock(return_value={"text": json.dumps(verdict), "usage": {}})):
            with self.assertRaisesRegex(ValueError, "verdict types"):
                await ev._judge_prediction("core-uplink", {}, {}, "gemini-3.8-flash", "live")


if __name__ == "__main__":
    unittest.main()
