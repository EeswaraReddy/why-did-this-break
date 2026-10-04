import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import investigator


class InvestigatorGroqConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True)
    def test_require_llm_configuration_accepts_groq(self):
        investigator.require_llm_configuration()

    @patch.dict(os.environ, {}, clear=True)
    def test_require_llm_configuration_raises_for_missing_key(self):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            investigator.require_llm_configuration()

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True)
    @patch("investigator.LiteLLMModel")
    @patch("investigator.Agent")
    def test_build_agent_uses_groq_model(self, mock_agent, mock_model):
        investigator.build_agent()

        mock_model.assert_called_once_with(
            model_id="groq/llama-3.1-8b-instant",
            client_args={"api_key": "test-key"},
        )
        mock_agent.assert_called_once()


if __name__ == "__main__":
    unittest.main()
