<div align="center">

# ⚡ TermiNews
### *Terminal-Based Multi-Source RAG News Intelligence Assistant*

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-243%2F243%20Passing-success?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![RAG Architecture](https://img.shields.io/badge/Architecture-6--Layer%20RAG-blueviolet?style=for-the-badge)](https://github.com/ishwaribhoyar/TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant)
[![LLM Support](https://img.shields.io/badge/LLM-OpenRouter%20%7C%20OpenAI-orange?style=for-the-badge&logo=openai&logoColor=white)](https://openrouter.ai/)
[![Cost](https://img.shields.io/badge/Default%20Cost-%240.00%20(Free)-green?style=for-the-badge)](https://github.com/ishwaribhoyar/TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<p align="center">
  <b>Bridging the LLM knowledge cutoff with real-time, triangulated multi-source retrieval, URL deduplication, prompt injection defense, and grounded AI synthesis right in your terminal.</b>
</p>

[Key Features](#-key-features) •
[System Architecture](#-system-architecture) •
[Live Terminal Preview](#-live-terminal-preview) •
[Quickstart](#-quickstart-guide) •
[Configuration](#-configuration--model-selection) •
[Engineering Highlights](#-engineering-highlights--robustness)

</div>

---

## 📌 The Problem & The Solution

| The Limitation | TermiNews Solution |
|---|---|
| **Knowledge Cutoff**: Standard LLMs cannot answer questions about current, real-time events. | **Live Multi-Source Retrieval**: Queries live Google News RSS, Reddit discussion feeds, and DuckDuckGo search in real-time. |
| **Hallucinations**: Generative models frequently fabricate facts, dates, and non-existent URLs. | **Strict Grounded Synthesis**: Generates answers strictly bounded inside `<retrieved_context>` with verified source citations `[1]`, `[2]`. |
| **Monolithic Fragility**: Web scrapers and APIs crash when a single external endpoint changes or rate-limits. | **Graceful Degradation**: 100% independent source isolation — if one service is unavailable, remaining sources and synthesis continue flawlessly. |
| **High API Cost**: Most RAG tools require expensive vector databases and mandatory paid subscriptions. | **Zero-Cost by Default**: Operates completely free using public RSS & web endpoints, with optional OpenRouter/OpenAI synthesis. |

---

## 🚀 Key Features

- 🌐 **Triangulated Multi-Source Intelligence**:
  - **Editorial / Journalistic**: Google News RSS for authoritative reporting.
  - **Community Sentiment**: Reddit API for public discourse, upvotes, and forum reactions.
  - **Catch-All Web Coverage**: DuckDuckGo search for niche blogs, technical releases, and fast-breaking updates.
- 🧠 **Multi-Model Grounded AI Synthesis**:
  - Plug-and-play support for **OpenRouter** (Claude 3.5, Llama 3.3, DeepSeek, GPT-4o-mini, Mistral, Gemini) and direct **OpenAI**.
- 🛡️ **Prompt Injection Defense**:
  - Treats all retrieved web data as untrusted reference material encapsulated in XML boundaries, preventing prompt overrides.
- ⚡ **Pure Functional Aggregation**:
  - Deterministic URL normalization and exact-duplicate stripping in under **1 millisecond**.
- 🖥️ **Adaptive Terminal Interface**:
  - Cross-platform width clamping (60–100 cols), text wrapping, UTF-8 checkmarks with ASCII fallback, and clean signal handling (`Ctrl+C`, `EOF`).
- 🧪 **Production-Grade Test Suite**:
  - **243 automated unit, integration, and security tests** running offline in ~5 seconds with 100% pass rate.

---

## 🏛️ System Architecture

TermiNews follows a strict **one-directional, 6-layer architecture** with pure boundaries and zero circular dependencies:

```mermaid
flowchart TD
    subgraph UI ["1. Presentation Layer"]
        CLI["Terminal CLI & Banner (terminal.py)"]
    end

    subgraph Orchestration ["2. Orchestration Layer"]
        Main["Interactive Session Loop (main.py)"]
    end

    subgraph Retrieval ["3. Retrieval Layer (Independent & Isolated)"]
        GN["Google News RSS (google_news.py)"]
        RD["Reddit API Search (reddit.py)"]
        DDG["DuckDuckGo Web (duckduckgo.py)"]
    end

    subgraph Aggregation ["4. Aggregation Layer"]
        Agg["Context Builder & Deduplication (aggregator.py)"]
        UC["UnifiedContext Object"]
    end

    subgraph Generation ["5. Synthesis Layer (Optional)"]
        LLM["Grounded Synthesis Engine (openai_synthesis.py)"]
        Prompt["<retrieved_context> Prompt Defense"]
        OR["OpenRouter / OpenAI API"]
    end

    subgraph Output ["6. Formatting Layer"]
        Fmt["Text Wrapper & Citation Resolver (terminal.py)"]
    end

    CLI -->|User Query| Main
    Main -->|Dispatches Query| GN
    Main -->|Dispatches Query| RD
    Main -->|Dispatches Query| DDG
    GN -->|NewsItem[]| Agg
    RD -->|RedditItem[]| Agg
    DDG -->|WebItem[]| Agg
    Agg --> UC
    UC -->|Query + Items| LLM
    LLM --> Prompt --> OR
    OR -->|SynthesizedAnswer + Citations| Fmt
    Fmt -->|Rendered View| CLI
```

---

## 📂 Layer Breakdown & Responsibilities

| Layer | Module Path | Core Responsibility | Purity Guarantee |
|---|---|---|---|
| **1. Presentation** | `presentation/terminal.py` | Welcome banner, terminal width detection, word wrapping, layout dividers | Zero retrieval or LLM imports |
| **2. Orchestration** | `main.py` | Interactive `while` loop, query lifecycle, signal trapping (`Ctrl+C`, `EOF`) | Isolated per-query state |
| **3. Sources** | `sources/*.py` | External network fetching, response parsing, and error encapsulation | Independent failure isolation |
| **4. Aggregation** | `aggregation/aggregator.py` | URL normalization, deduplication, provenance tracking, `UnifiedContext` | Pure in-memory transformer (< 1ms) |
| **5. Synthesis** | `synthesis/openai_synthesis.py`| XML context framing, citation ID extraction, OpenRouter/OpenAI routing | Zero independent web retrieval |
| **6. Formatting** | `presentation/terminal.py` | Citation mapping (`[SOURCE_001]` ➔ `[1] Reuters`), clean terminal display | Pure string output |

---

## 📺 Live Terminal Preview

```text
==================================================
   TERMINAL NEWS ASSISTANT (TermiNews)
==================================================

Retrieve live information from Google News RSS, Reddit, and DuckDuckGo,
aggregate results, and synthesize a grounded AI summary.
Type a search query and press Enter.
Type "exit" or press Ctrl-C to quit.

  ✓ Python environment ready
  ✓ Google News RSS source ready
  ✓ Reddit source ready (requires credentials)
  ✓ DuckDuckGo web search source ready
  ✓ Context aggregation layer ready
  ✓ Optional LLM synthesis layer ready (via OpenRouter / OpenAI)
==================================================

Search > quantum computing breakthroughs

========================================
          GOOGLE NEWS RESULTS
========================================
Query: quantum computing breakthroughs

1. IBM Connects First Modular Cryogenic Systems for Scalable Quantum Computing
   Source:    IBM Newsroom
   Published: 2026-08-18 14:30 UTC
   Link:      https://news.google.com/rss/articles/...

2. The Role of Silicon Photonics in Delivering Usable Quantum Systems
   Source:    The Quantum Insider
   Published: 2026-08-18 13:15 UTC
   Link:      https://news.google.com/rss/articles/...

========================================
               AI SUMMARY
========================================
Based on mid-2026 developments, the quantum computing sector is accelerating
across hardware scalability and commercialization:

* Hardware Scalability: IBM achieved a major milestone by connecting modular
  cryogenic systems, paving the way for fault-tolerant architectures [SOURCE_001].
* Silicon Photonics: Recent industry analyses identify silicon photonics as
  the critical technology for practical optical interconnects [SOURCE_002].

Sources: [1] IBM Newsroom, [2] The Quantum Insider
========================================
```

---

## ⚡ Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/ishwaribhoyar/TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant.git
cd TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant
```

### 2. Set Up Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run TermiNews
```bash
python run.py
```
*(Works out-of-the-box at **$0.00 cost** as a multi-source news aggregator!)*

---

## ⚙️ Configuration & Model Selection

To enable **Grounded AI Synthesis**, copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Option A: OpenRouter (Recommended — Multi-Model Access)
```env
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

#### Supported OpenRouter Models:
| Model Name | `OPENROUTER_MODEL` Setting | Best For |
|---|---|---|
| **GPT-4o Mini** | `openai/gpt-4o-mini` *(Default)* | Fast, high precision, cost-efficient |
| **DeepSeek Chat** | `deepseek/deepseek-chat` | Exceptional reasoning & affordability |
| **Llama 3.3 70B** | `meta-llama/llama-3.3-70b-instruct` | Open-weights, deep factual synthesis |
| **Mistral Small** | `mistralai/mistral-small-24b-instruct-2501` | Ultra-low latency summaries |

### Option B: Direct OpenAI API Key
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Option C: Optional Reddit Developer Credentials
```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=terminal-news-assistant/0.1
```

---

## 🛡️ Engineering Highlights & Robustness

### 1. 243/243 Deterministic Test Coverage
```bash
pytest -v
============================= 243 passed in 5.16s =============================
```
- **Hermetic & Fast**: All 243 tests execute in under 6 seconds using offline fixtures and mock wrappers.
- **Contract Testing**: Every phase preserves strict backwards-compatible data contracts.

### 2. Fault Isolation Matrix
| Scenario | Behavior | Outcome |
|---|---|---|
| **DuckDuckGo Rate-Limit** | Catches `429/202` response, isolates exception | Google News & AI Synthesis render normally |
| **Missing Reddit Key** | Triggers `RedditCredentialsError` fallback | User gets notice; pipeline continues |
| **Unset LLM Key** | Detects missing key gracefully | Shows `[NOTE]` tip; displays full raw news |
| **Empty / Whitespace Input** | Input validation interceptor | Reprompts user without redundant API calls |
| **Process Interruption** | Catches `Ctrl+C` (`KeyboardInterrupt`) & `Ctrl+D` (`EOFError`) | Prints `\nGoodbye.` with exit code `0` |

### 3. Security Hygiene
- **Zero Exposed Secrets**: Automated AST and regex scans verify zero hardcoded tokens.
- **Path Portability**: Zero machine-specific absolute paths (`C:\Users\...` or `/home/...`).
- **Prompt Isolation**: System instructions force the LLM to treat retrieved web data as untrusted references.

---

## 🛠️ Tech Stack

- **Core Runtime**: Python 3.10+ (Standard Library: `urllib`, `textwrap`, `shutil`, `re`, `time`)
- **RSS Parsing**: `feedparser==6.0.11`
- **Reddit Client**: `praw==7.7.1`
- **Web Search**: `duckduckgo-search==6.3.7`
- **LLM Client**: `openai>=1.0.0` *(Configured for OpenRouter & OpenAI endpoints)*
- **Testing**: `pytest==8.3.2`

---

## 🗺️ Project Roadmap & Extensions

- [x] Phase 0: Foundation & Environment Setup
- [x] Phase 1: Google News RSS Source Component
- [x] Phase 2: Reddit Source & Credential Isolation
- [x] Phase 3: DuckDuckGo Web Search Fallback
- [x] Phase 4: Context Aggregation & Deduplication
- [x] Phase 5: Grounded LLM Synthesis Engine
- [x] Phase 6: Terminal Formatting & Text Wrapping
- [x] Phase 7: Interactive Multi-Query Session Loop
- [x] Phase 8: Production Audit, Hardening & OpenRouter Multi-Model Integration
- [ ] Export query briefings to Markdown (`--export notes.md`)
- [ ] Topic tracking bookmarking

---

## 👤 Author

**Ishwari Bhoyar**
- **GitHub**: [@ishwaribhoyar](https://github.com/ishwaribhoyar)
- **Repository**: [TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant](https://github.com/ishwaribhoyar/TermiNews-Terminal-Based-Multi-Source-RAG-News-Assistant.git)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — feel free to use, modify, and distribute for personal and educational projects.
