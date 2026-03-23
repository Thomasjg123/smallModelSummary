"""Configuration for Wikipedia summarization context tests."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ChunkingMethod(Enum):
    SECTION = "section"
    FIXED = "fixed"


class DoneSignalType(Enum):
    NONE = "none"
    XML = "xml"
    JSON = "json"
    NATURAL = "natural"


class PromptStyle(Enum):
    BASIC = "basic"
    EXPLICIT = "explicit"
    WITH_EXAMPLE = "with_example"


@dataclass
class TestConfig:
    """Configuration for a single test run."""
    id: str
    name: str
    chunking_method: ChunkingMethod
    fixed_chunk_size: Optional[int] = None  # Only for FIXED method
    include_previous_summary: bool = True
    max_summary_tokens: int = 1000
    save_each_chunk: bool = True
    done_signal_type: DoneSignalType = DoneSignalType.NONE
    allow_early_completion: bool = False
    prompt_style: PromptStyle = PromptStyle.BASIC
    max_context_tokens: int = 20000
    max_words: int = 1000  # Soft guidance for model
    two_phase_summary: bool = False  # Phase 1: summarize each section, Phase 2: combine

    @property
    def config_id(self) -> str:
        """Generate a unique config ID for this test."""
        parts = [self.chunking_method.value]
        if self.chunking_method == ChunkingMethod.FIXED:
            parts.append(f"{self.fixed_chunk_size}k")
        if self.include_previous_summary:
            parts.append("with_ctx")
            parts.append(f"{self.max_summary_tokens}tok")
        else:
            parts.append("no_ctx")
        parts.append(self.done_signal_type.value)
        if self.allow_early_completion:
            parts.append("early")
        else:
            parts.append("full")
        if self.prompt_style != PromptStyle.BASIC:
            parts.append(self.prompt_style.value)
        return "_".join(parts)


@dataclass
class Article:
    """Wikipedia article configuration."""
    name: str
    title: str
    description: str
    estimated_tokens: int = 50000


# Wikipedia articles to test
ARTICLES = [
    Article(
        name="world_war_ii",
        title="World War II",
        description="Global conflict 1939-1945",
        estimated_tokens=55000,
    ),
    Article(
        name="united_states",
        title="United States",
        description="Country in North America",
        estimated_tokens=52000,
    ),
    Article(
        name="python_programming",
        title="Python (programming language)",
        description="Programming language",
        estimated_tokens=48000,
    ),
    Article(
        name="solar_system",
        title="Solar System",
        description="Planetary system",
        estimated_tokens=50000,
    ),
    Article(
        name="history_of_internet",
        title="History of the Internet",
        description="Evolution of the Internet",
        estimated_tokens=45000,
    ),
    Article(
        name="french_revolution",
        title="French Revolution",
        description="Revolution in France 1789-1799",
        estimated_tokens=52000,
    ),
    Article(
        name="human_genome",
        title="Human genome",
        description="Complete set of human DNA",
        estimated_tokens=47000,
    ),
    Article(
        name="artificial_intelligence",
        title="Artificial intelligence",
        description="Intelligence demonstrated by machines",
        estimated_tokens=50000,
    ),
    Article(
        name="climate_change",
        title="Climate change",
        description="Long-term changes in climate",
        estimated_tokens=48000,
    ),
    Article(
        name="classical_music",
        title="Classical music",
        description="Art music produced in Western tradition",
        estimated_tokens=51000,
    ),
]

# Test configurations - 15 total for WW2
TEST_CONFIGS = [
    # Basic prompt style configs (1-11)
    TestConfig(
        id="01",
        name="Small, Section, no context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=False,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.BASIC,
        two_phase_summary=True,
    ),
    TestConfig(
        id="02",
        name="Small, Section, with context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="03",
        name="Small, Section, XML done, early",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="04",
        name="Small, Section, XML done, full",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=False,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="05",
        name="Small, Section, compressed (500)",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=500,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="06",
        name="Small, Fixed 2k chunks",
        chunking_method=ChunkingMethod.FIXED,
        fixed_chunk_size=2000,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="07",
        name="Small, Fixed 4k chunks",
        chunking_method=ChunkingMethod.FIXED,
        fixed_chunk_size=4000,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="08",
        name="Small, JSON done signal",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.JSON,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="09",
        name="Big, Section, no context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=False,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.BASIC,
        two_phase_summary=True,
    ),
    TestConfig(
        id="10",
        name="Big, Section, with context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.BASIC,
    ),
    TestConfig(
        id="11",
        name="Big, Section, XML done, early",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.BASIC,
    ),
    # Explicit prompt style configs (12-15)
    TestConfig(
        id="12",
        name="Small, Explicit, no context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=False,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.EXPLICIT,
    ),
    TestConfig(
        id="13",
        name="Small, Explicit, XML early",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.EXPLICIT,
    ),
    TestConfig(
        id="14",
        name="Big, Explicit, no context",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=False,
        done_signal_type=DoneSignalType.NONE,
        allow_early_completion=False,
        prompt_style=PromptStyle.EXPLICIT,
    ),
    TestConfig(
        id="15",
        name="Big, Explicit, XML early",
        chunking_method=ChunkingMethod.SECTION,
        include_previous_summary=True,
        max_summary_tokens=1000,
        done_signal_type=DoneSignalType.XML,
        allow_early_completion=True,
        prompt_style=PromptStyle.EXPLICIT,
    ),
]

# Model configurations
@dataclass
class ModelConfig:
    """Model API configuration."""
    base_url: str
    model_name: str
    display_name: str
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 120


def _get_env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


SMALL_MODEL = ModelConfig(
    base_url=_get_env_str("DEBUGCLI_SMALL_MODEL_BASE_URL", "http://thomas-latop.local:8080/v1"),
    model_name=_get_env_str("DEBUGCLI_SMALL_MODEL_NAME", "Qwen3.5 0.8b q8"),
    display_name=_get_env_str("DEBUGCLI_SMALL_MODEL_DISPLAY_NAME", "Small (0.8B)"),
    temperature=_get_env_float("DEBUGCLI_SMALL_MODEL_TEMPERATURE", 0.3),
    max_tokens=_get_env_int("DEBUGCLI_SMALL_MODEL_MAX_TOKENS", 2048),
    timeout=_get_env_int("DEBUGCLI_SMALL_MODEL_TIMEOUT", 120),
)

BIG_MODEL = ModelConfig(
    base_url=_get_env_str("DEBUGCLI_BIG_MODEL_BASE_URL", "http://server2.local:8000/v1"),
    model_name=_get_env_str("DEBUGCLI_BIG_MODEL_NAME", "llama"),
    display_name=_get_env_str("DEBUGCLI_BIG_MODEL_DISPLAY_NAME", "Big (Llama)"),
    temperature=_get_env_float("DEBUGCLI_BIG_MODEL_TEMPERATURE", 0.3),
    max_tokens=_get_env_int("DEBUGCLI_BIG_MODEL_MAX_TOKENS", 4096),
    timeout=_get_env_int("DEBUGCLI_BIG_MODEL_TIMEOUT", 300),
)

# Configs for small model (01-08, 12-13)
SMALL_MODEL_CONFIGS = ["01", "02", "03", "04", "05", "06", "07", "08", "12", "13"]

# Configs for big model (09-11, 14-15)
BIG_MODEL_CONFIGS = ["09", "10", "11", "14", "15"]

# Paths
BASE_DIR = Path(__file__).parent
ARTICLES_DIR = BASE_DIR / "articles"
RUNS_DIR = BASE_DIR / "runs"

# Ensure directories exist
ARTICLES_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)
