"""Domain-specific errors for clear failure boundaries in the pipeline."""


class LumenError(Exception):
    """Base class for all Lumen errors."""


class ConfigurationError(LumenError):
    """Missing or invalid configuration (env, model names, keys)."""


class SearchError(LumenError):
    """Search provider failure or empty result when not allowed."""


class FetchError(LumenError):
    """HTTP fetch or parse failure for a source URL."""


class RetrievalError(LumenError):
    """Vector store or embedding failure."""


class SynthesisError(LumenError):
    """LLM synthesis failure or schema validation failure on output."""
