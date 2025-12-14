from __future__ import annotations

import subprocess
import sys
from typing import Optional

from services import config_manager


class AIAssistant:
    # provides lightweight helper responses for the dashboards using gemini

    def get_response(self, domain_name: str, domain_summary_text: str, user_question: str) -> str:
        # return an assistant response or a helpful fallback message
        # the prompt is short so students can quickly see helpful text
        user_question = (user_question or "").strip()
        if not user_question:
            return "Please enter a question for the assistant."

        provider = config_manager.get_current_provider()
        model = config_manager.get_current_model(provider)
        api_key = config_manager.get_api_key(provider)
        env_var = config_manager.get_provider_env_var(provider)
        if not api_key:
            return f"Add a value for {env_var} in Settings to enable the assistant."

        prompt = (
            "You are an AI helper for a university coursework dashboard. "
            "Respond with short, actionable guidance suitable for a junior analyst. "
            f"Domain: {domain_name}. Current summary: {domain_summary_text}. "
            f"User question: {user_question}"
        )

        return self._call_gemini(model, api_key, prompt)

    def _call_gemini(self, model: str, api_key: str, prompt: str) -> str:
        # call gemini models when that provider is active
        genai = self._load_gemini_client()
        if genai is None:
            return "Gemini client is missing. Please run `pip install google-generativeai`."
        try:
            genai.configure(api_key=api_key)
            generative_model = genai.GenerativeModel(model_name=model or "gemini-2.5-flash")
            response = generative_model.generate_content(prompt)
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content.parts:
                        return " ".join(part.text for part in candidate.content.parts if hasattr(part, "text")).strip()
            return "The assistant could not generate a complete reply."
        except Exception as exc:  # pragma: no cover
            return f"Gemini error: {exc}"[:200]

    def _load_gemini_client(self):
        # lazily import gemini and attempt auto install if needed
        try:
            import google.generativeai as genai  # type: ignore

            return genai
        except ImportError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "google-generativeai"],
                    check=True,
                    capture_output=True,
                )
                import google.generativeai as genai  # type: ignore

                return genai
            except Exception:
                return None
