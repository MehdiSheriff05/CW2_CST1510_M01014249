from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st

# optional dotenv import so keys can be persisted locally
try:  # pragma: no cover - dependency optional for hosted environments
    from dotenv import load_dotenv, set_key
    DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover
    DOTENV_AVAILABLE = False

    def load_dotenv(*_, **__):
        return False

    def set_key(*_, **__):  # type: ignore
        raise RuntimeError("python-dotenv is required to save keys locally. Run `pip install python-dotenv`.") from None

# path to optional .env file for local storage
ENV_PATH = Path('.env')
load_dotenv(dotenv_path=ENV_PATH)

PROVIDERS: Dict[str, Dict[str, object]] = {
    'gemini': {
        'label': 'Gemini',
        'env_var': 'GEMINI_API_KEY',
        # keep only the widely available flash model to avoid 404 errors
        'models': ['gemini-2.5-flash'],
        'default_model': 'gemini-2.5-flash',
    },
}
DEFAULT_PROVIDER = 'gemini'


def ensure_defaults() -> None:
    # make sure provider/model/session stores exist
    st.session_state.setdefault('llm_provider', DEFAULT_PROVIDER)
    provider = st.session_state['llm_provider']
    if provider not in PROVIDERS:
        st.session_state['llm_provider'] = DEFAULT_PROVIDER
        provider = DEFAULT_PROVIDER
    st.session_state.setdefault('llm_models', {})
    models_map = st.session_state['llm_models']
    if provider not in models_map:
        models_map[provider] = PROVIDERS[provider]['default_model']
    st.session_state.setdefault('llm_api_keys', {})


def get_provider_label(slug: str) -> str:
    # return a friendly name for dropdowns
    return PROVIDERS.get(slug, {}).get('label', slug.title())


def get_provider_options() -> List[str]:
    # a list of provider slugs for select boxes
    return list(PROVIDERS.keys())


def get_provider_models(provider: str) -> List[str]:
    # expose the models we know for a provider slug
    data = PROVIDERS.get(provider, {})
    return list(data.get('models', [])) or [data.get('default_model', '')]


def get_current_provider() -> str:
    # read the active provider from session state
    ensure_defaults()
    provider = st.session_state.get('llm_provider', DEFAULT_PROVIDER)
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
        st.session_state['llm_provider'] = DEFAULT_PROVIDER
    return provider


def set_current_provider(provider: str) -> None:
    # update provider and ensure we store a default model
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    st.session_state['llm_provider'] = provider
    models_map = st.session_state.setdefault('llm_models', {})
    models_map.setdefault(provider, PROVIDERS[provider]['default_model'])


def get_current_model(provider: Optional[str] = None) -> str:
    # fetch the current model for given provider
    ensure_defaults()
    provider = provider or get_current_provider()
    models_map = st.session_state.get('llm_models', {})
    current = models_map.get(provider)
    if current not in get_provider_models(provider):
        current = PROVIDERS[provider]['default_model']
        models_map[provider] = current
    return current


def set_current_model(model: str, provider: Optional[str] = None) -> None:
    # update stored model for a provider
    provider = provider or get_current_provider()
    if model not in get_provider_models(provider):
        model = PROVIDERS[provider]['default_model']
    models_map = st.session_state.setdefault('llm_models', {})
    models_map[provider] = model


def _resolve_key(provider: str) -> Tuple[Optional[str], str]:
    # priority order: session override, secrets, environment, missing
    ensure_defaults()
    env_var = PROVIDERS[provider]['env_var']
    session_keys = st.session_state.get('llm_api_keys', {})
    session_key = session_keys.get(provider)
    if session_key:
        return session_key, 'session'
    try:
        secret_key = st.secrets.get(env_var)
    except Exception:
        secret_key = None
    if secret_key:
        return secret_key, 'secrets'
    env_key = os.environ.get(env_var)
    if env_key:
        return env_key, 'env'
    return None, 'missing'


def get_api_key(provider: Optional[str] = None) -> Optional[str]:
    # helper returns only the key string
    provider = provider or get_current_provider()
    key, _ = _resolve_key(provider)
    return key


def get_api_key_source(provider: Optional[str] = None) -> str:
    # helper returns where the key came from
    provider = provider or get_current_provider()
    _, source = _resolve_key(provider)
    return source


def store_session_key(provider: str, key: str) -> bool:
    # keep a key only for current session
    if not key:
        return False
    ensure_defaults()
    st.session_state.setdefault('llm_api_keys', {})[provider] = key
    return True


def clear_session_key(provider: str) -> None:
    # forget a session key for a provider
    st.session_state.setdefault('llm_api_keys', {}).pop(provider, None)


def get_provider_env_var(provider: str) -> str:
    # return env var name for a provider slug
    return PROVIDERS.get(provider, {}).get('env_var', '')


def is_hosted_environment() -> bool:
    # rough heuristics to detect community cloud and similar envs
    home = os.environ.get('HOME', '')
    return (
        os.environ.get('STREAMLIT_RUNTIME', '').lower() == 'cloud'
        or os.environ.get('STREAMLIT_CLOUD', '').lower() == 'true'
        or home.startswith('/home/appuser')
    )


def can_persist_locally() -> bool:
    # true when dotenv is available and we seem to be local
    return DOTENV_AVAILABLE and not is_hosted_environment()


def save_key_locally(provider: str, key: str) -> bool:
    # write key to .env when allowed
    if not key or not can_persist_locally():
        return False
    env_var = get_provider_env_var(provider)
    if not env_var:
        return False
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), env_var, key)
    return True


def get_status(provider: Optional[str] = None) -> Dict[str, str]:
    # return details used by the settings ui
    provider = provider or get_current_provider()
    model = get_current_model(provider)
    key, source = _resolve_key(provider)
    status = {
        'provider': get_provider_label(provider),
        'model': model,
        'key_present': 'yes' if key else 'no',
        'key_source': source,
    }
    if source == 'env':
        status['key_source'] = '.env/env vars'
    elif source == 'secrets':
        status['key_source'] = 'st.secrets'
    elif source == 'session':
        status['key_source'] = 'session'
    else:
        status['key_source'] = 'missing'
    return status
