"""Subscription routing, bounded investigation, and usage contracts (no inference)."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import codex_runner as runner
import sade_eval as ev


class CodexRunnerTests(unittest.TestCase):
    def test_api_keys_are_blank_and_subscription_mode_is_explicit(self):
        with tempfile.TemporaryDirectory() as cwd, patch.dict(runner.os.environ, {'OPENAI_API_KEY': 'fake-key', 'CODEX_API_KEY': 'fake-key', 'ANTHROPIC_API_KEY': 'fake-key'}):
            config = runner._config(cwd, subscription=True)
            self.assertEqual(config.env['OPENAI_API_KEY'], '')
            self.assertEqual(config.env['CODEX_API_KEY'], '')
            self.assertEqual(config.env['ANTHROPIC_API_KEY'], '')
            self.assertIn('forced_login_method="chatgpt"', config.config_overrides)
            self.assertIn('features.shell_tool=false', config.config_overrides)

    def test_api_login_is_rejected_before_models_or_inference(self):
        client = SimpleNamespace(account=AsyncMock(return_value=SimpleNamespace(account=SimpleNamespace(root=SimpleNamespace(type='apiKey')))), models=AsyncMock())
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch('openai_codex.AsyncCodex', return_value=context), self.assertRaisesRegex(RuntimeError, 'API billing fallback is disabled'):
            asyncio.run(runner.check_subscription('gpt-6.1-sol'))
        client.models.assert_not_called()

    def test_round_budget_stops_unknown_tools_without_executing_them(self):
        response = SimpleNamespace(final_response=json.dumps({'tool_calls': [{'name': 'Bash', 'arguments_json': '{"command":"forbidden"}'}], 'final_text': ''}), usage=None)
        thread = SimpleNamespace(run=AsyncMock(return_value=response))
        client = SimpleNamespace(account=AsyncMock(return_value=SimpleNamespace(account=SimpleNamespace(root=SimpleNamespace(type='chatgpt')))), thread_start=AsyncMock(return_value=thread))
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch('openai_codex.AsyncCodex', return_value=context), patch.object(runner, '_ensure_isolated', AsyncMock()):
            result = asyncio.run(runner.run('gpt-6.1-sol', 'test', 'test', 2, {}, Path('.')))
        self.assertTrue(result['hit_max_turns'])
        self.assertEqual(thread.run.await_count, 2)
        self.assertIn('Unknown or unavailable tool', result['trace'][1]['content'])
        self.assertEqual(result['auth_mode'], 'codex-subscription')
        self.assertIsNone(result['total_cost_usd'])

    def test_cached_input_is_not_double_counted(self):
        usage = SimpleNamespace(input_tokens=1000, cached_input_tokens=800, output_tokens=30)
        result = SimpleNamespace(usage=SimpleNamespace(total=usage))
        normalized = runner._usage(result)
        self.assertEqual(normalized['input_tokens'], 200)
        self.assertEqual(normalized['cache_read_input_tokens'], 800)
        self.assertEqual(sum(normalized.values()), 1030)

    def test_gpt_judge_uses_codex_and_existing_strict_quality_schema(self):
        quality = {'explanation_correct': True, 'repair_correct': True, 'explanation_reason': 'Supported.', 'repair_reason': 'Targeted.'}
        prediction = {'diagnosis_text': 'Evidence', 'repair_text': 'Repair'}
        with patch.object(runner, 'judge', AsyncMock(return_value={'text': json.dumps(quality), 'usage': {}})) as judge:
            result = asyncio.run(ev._judge_prediction('core-uplink', prediction, {}, 'gpt-6.1-terra', 'live'))
        judge.assert_awaited_once()
        self.assertEqual(result['model'], 'gpt-6.1-terra')
        self.assertTrue(result['repair_correct'])
        self.assertIsNone(result['total_cost_usd'])


if __name__ == '__main__':
    unittest.main()
