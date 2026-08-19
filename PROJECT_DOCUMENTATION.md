# Terminal News Assistant — Project Documentation

## 1. Project Overview

The Terminal News Assistant is a command-line AI tool that answers "what is happening right now" queries by retrieving live information from three independent, free sources — Google News RSS, Reddit, and DuckDuckGo web search — merging their results, and optionally using a large language model (LLM) to synthesize that raw information into a clear, natural-language answer.

The project exists to solve a specific limitation of standalone LLMs: their knowledge is frozen at a training cutoff date, so they cannot natively answer questions about current events. This tool bridges that gap using a lightweight Retrieval-Augmented Generation (RAG) pattern — fetching fresh, real-world data at the moment of the query and feeding it to the model as context, rather than relying on the model's memorized training data.

The project is intentionally scoped to be simple, free to run, and terminal-based, making it approachable as a learning project while still reflecting real-world patterns used in production RAG systems.

---

## 2. Goals and Non-Goals

### 2.1 Goals
- Provide current, multi-perspective news information (official headlines, public discussion, and general web results) from a single terminal interface.
- Keep the tool free to run by default, using sources that require no paid subscription.
- Make the AI synthesis step optional so the tool remains fully functional even without any LLM API key.
- Keep the architecture simple enough to be understood, modified, and extended by a single developer without prior RAG experience.
- Ensure the tool never fails completely due to one source being unavailable or misconfigured.

### 2.2 Non-Goals
- This is not a production-grade, multi-user news platform. It is a personal/learning tool.
- It does not attempt deep fact-verification or bias detection across sources.
- It does not persist conversation history or user profiles between sessions.
- It does not aim for real-time streaming updates; it retrieves fresh data per query, on demand.

---

## 3. User Flow

This section describes the experience from the perspective of the person using the tool, from launch to exit.

### 3.1 Step-by-step user journey

1. **Launch** — The user starts the assistant from a terminal. A welcome banner and brief usage instructions are displayed.
2. **Prompt appears** — A persistent input prompt waits for the user's query, with no restrictions on phrasing (topic word, full question, etc.).
3. **User enters a query** — For example, a topic like "AI regulation" or a full question like "what's happening with the stock market today."
4. **Results appear incrementally** — As each of the three sources responds, its section of results is displayed immediately, rather than the user waiting silently for everything to finish at once. This keeps the experience transparent rather than feeling like a black box.
5. **Optional AI summary appears** — If the AI synthesis layer is enabled, a final summary section appears beneath the three raw source sections, giving a synthesized, plain-language answer drawing on everything retrieved.
6. **Prompt reappears** — The user can immediately ask a new question, building on the same session.
7. **Session ends** — The user types an exit command (or interrupts the program), and the session closes cleanly with a farewell message rather than an error.

### 3.2 User experience principles
- **No dead ends**: a missing configuration (like no Reddit credentials) or a temporary network issue with one source never halts the whole tool — it degrades gracefully and continues with whatever succeeded.
- **Transparency over black-box behavior**: the user sees exactly which sources contributed what information, and whether an AI summary was generated or skipped, rather than receiving an opaque single answer.
- **Conversational continuity within a session**: multiple queries can be asked back-to-back without relaunching the program, though each query is treated independently (no memory of prior queries is retained).

---

## 4. System Flow (Internal Processing per Query)

This section describes what happens internally, in order, each time the user submits a query.

1. The user's query string is captured by the input layer and handed to the orchestration logic.
2. The query is sent to the **Google News RSS** source, which returns a set of current headlines matching the query, each with a title, originating publication, publish time, and link.
3. The query is sent to the **Reddit search** source (if credentials are configured), which returns a set of relevant discussion posts, each with a title, subreddit, upvote count, comment count, and link. If Reddit is not configured or the request fails, this step is skipped with a clear notice, and processing continues.
4. The query is sent to the **DuckDuckGo web search** source, which returns a set of general web results, each with a title, snippet, and link. If this source is temporarily unavailable, it is likewise skipped without halting the process.
5. As each source completes, its results are immediately formatted and displayed to the user, and simultaneously appended to a shared internal "context" collection used for the optional AI step.
6. Once all three sources have been attempted, the system checks whether an AI synthesis capability is available (i.e., whether an LLM API key has been configured).
   - If available, the full collected context along with the original query is sent to the LLM with an instruction to answer strictly using the retrieved context, and the resulting answer is displayed as a final "AI Summary" section.
   - If not available, the system displays a short note suggesting that an AI summary could be enabled, and the raw aggregated results from the three sources serve as the complete answer.
7. Control returns to the input prompt, ready for the next query.

### 4.1 Processing characteristics
- The three sources are queried **sequentially**, not in parallel. This was a deliberate simplicity choice — it keeps the internal logic easy to trace and debug, at the cost of the total response time being the sum of all individual source response times rather than the maximum of them.
- Each source is **isolated**: a failure or misconfiguration in one has no effect on the others. This isolation is what allows the tool to degrade gracefully rather than fail outright.

---

## 5. Architecture (Layered Breakdown)

The system is organized into six conceptual layers. Each layer has a single clear responsibility and does not need to know the internal details of the layers around it.

### 5.1 Presentation Layer
Responsible for all direct interaction with the user: displaying the welcome banner, showing the input prompt, reading the raw query text, and printing all output (headers, formatted sections, wrapped paragraphs). This layer has no knowledge of *how* information is retrieved or synthesized — it only displays what it is given and collects what the user types.

### 5.2 Orchestration Layer
The coordinating layer that runs once per user query. Its responsibilities:
- Receiving the query from the Presentation Layer.
- Invoking each of the three source-retrieval components in sequence.
- Collecting each source's normalized output into a shared context structure.
- Determining whether the AI synthesis step should run, based on whether the necessary configuration (an LLM key) is present.
- Passing the final combined output back to the Presentation Layer for display.

This layer is the "control center" of the system — it does not fetch data itself, nor does it format output for display; it simply directs the flow between the layers that do.

### 5.3 Source Layer (Retrieval)
Three independent, self-contained components, each responsible for exactly one external information source:

- **Google News component**: Queries Google's public news RSS feed for the given search term and normalizes the returned entries into a consistent structure (headline, publication name, publish date, link). Requires no authentication or API key, and effectively has no meaningful usage limit for personal use since it relies on a public feed rather than a metered API.

- **Reddit component**: Authenticates against Reddit's API using free developer credentials (a client ID and secret obtained by registering a "script" app), searches broadly across Reddit for posts relevant to the query, and normalizes results into a consistent structure (post title, subreddit, score, comment count, link). This is the one source in the system that requires a one-time free setup step; without it, the component is simply skipped.

- **DuckDuckGo component**: Performs a live, general web search for the query and normalizes results into a consistent structure (title, snippet, link). Requires no authentication or API key. This source acts as the broadest "catch-all," surfacing content the more structured news and discussion sources might miss, such as very recent blog posts or niche publications.

Each of these three components fails independently — an error, timeout, or missing configuration in one never propagates to or blocks the others. This isolation is the architectural foundation of the tool's graceful-degradation behavior.

### 5.4 Aggregation / Context-Building Layer
Takes the normalized output from all three source components (whichever succeeded) and merges them into a single unified context representation. This is the "retrieval-to-context" step of the RAG pattern — turning three separately-shaped datasets into one coherent body of information that can be reasoned over as a whole, whether by the optional AI layer or simply by the human reader scanning the terminal output.

### 5.5 Synthesis Layer (Optional)
If an LLM capability is configured, this layer takes the aggregated context along with the user's original question and sends it to the language model with explicit instructions to answer using only the provided context — a constraint intended to reduce the likelihood of the model inventing information beyond what was actually retrieved. The result is a natural-language answer that reads as a coherent response rather than a raw list of snippets. This layer is entirely optional and the system is fully functional without it.

### 5.6 Output Formatting Layer
Takes whatever combination of raw source sections and (optionally) the AI-synthesized summary exists at the end of a query cycle, and renders it into a consistent, readable terminal format: clearly separated section headers per source, numbered entries for scanability, and wrapped text so long snippets or summaries remain readable within a standard terminal window width.

### 5.7 Layer Interaction Summary
The six layers interact in a strict one-directional flow for each query: Presentation feeds a query into Orchestration, Orchestration fans out to the three Source components, their results flow into Aggregation, Aggregation optionally feeds Synthesis, and the final combined result flows back through Output Formatting to Presentation. No layer reaches "backward" or skips ahead — this predictability is what keeps the system easy to reason about despite combining three external services and an optional AI step.

---

## 6. Why This Design Qualifies as RAG

Retrieval-Augmented Generation is a pattern where a language model's response is grounded in freshly retrieved external data rather than relying solely on what the model learned during training. This project implements that pattern directly:

- **Retrieval**: The three source components (Google News, Reddit, DuckDuckGo) fetch live, current data at the moment of the query — not from the model's training data.
- **Augmentation**: The Aggregation layer merges these three separately-retrieved datasets into a single unified context.
- **Generation**: The Synthesis layer (when enabled) has the language model read that freshly assembled context and produce a coherent, natural-language answer grounded in it.

The practical benefit is that answers reflect the actual current state of the world at query time, rather than being limited to whatever the model happened to know as of its training cutoff — which is the entire purpose of a "current news" assistant.

---

## 7. Detailed Feature Breakdown

### 7.1 Multi-source retrieval
The tool does not rely on a single source of truth. It deliberately combines three qualitatively different types of information for a single query:
- **Official/editorial framing** via Google News (how news outlets are reporting the story).
- **Public discussion and sentiment** via Reddit (how people are reacting to and discussing the story).
- **Broad web coverage** via DuckDuckGo (anything the first two sources might miss, including very recent or niche content).

This triangulation gives the user a more rounded picture than any single source could provide on its own.

### 7.2 Graceful degradation
Every source is treated as independently fallible. If Reddit credentials are missing, if DuckDuckGo is temporarily rate-limited, or if any single network call fails, that specific source is skipped with a clear, short notice — the rest of the pipeline proceeds unaffected. The user is never left with a crashed program or a confusing error; at worst, they simply get results from fewer than three sources.

### 7.3 Optional AI synthesis
The AI/LLM step is strictly additive rather than a hard requirement. The tool is fully usable as a pure aggregator with zero API keys and zero cost. When an LLM key is supplied, the tool gains the ability to produce a single, readable, synthesized answer instead of requiring the user to read and mentally combine three separate lists of results themselves. This design choice keeps the "free and simple" goal intact while still allowing for a more polished experience when the user chooses to enable it.

### 7.4 Conversational session loop
The tool runs as a persistent session rather than a one-shot command. A user can ask any number of unrelated or related queries in a row without restarting the program, closing it only when they explicitly choose to exit. Each query, however, is processed independently — the system does not carry memory of earlier questions within the session, keeping the internal logic simple and predictable.

### 7.5 Incremental, transparent output
Rather than presenting a single merged answer with no indication of where information came from, the tool displays each source's contribution as a distinct, clearly labeled section, in the order the sources were queried. This transparency lets the user judge the credibility and nature of each piece of information themselves, and makes it obvious which sources succeeded or were skipped for a given query.

### 7.6 Readable terminal presentation
Output is formatted specifically for a standard terminal window: clear section banners separate each source's results, entries are numbered for easy scanning, and longer text such as web snippets or the AI summary is wrapped to a consistent width so it remains legible rather than spilling unpredictably across the screen.

### 7.7 Zero-cost-by-default operation
Two of the three sources (Google News RSS and DuckDuckGo) require no signup, no API key, and no usage cost whatsoever. The third (Reddit) requires only a one-time free developer registration with a generous rate limit suitable for personal use. The only component of the system that could ever incur a cost is the optional AI synthesis step, and the tool is designed so that omitting it entirely still results in a fully functional news aggregator.

---

## 8. Design Trade-offs and Rationale

| Decision | Rationale | Trade-off Accepted |
|---|---|---|
| Sequential source calls instead of parallel | Keeps internal logic simple and easy to trace/debug | Slightly slower per-query response time |
| AI synthesis is optional | Keeps the tool genuinely free and fully functional without any paid service | The most "assistant-like" feature is the one requiring a paid API key |
| DuckDuckGo used via its unofficial search interface | No API key or signup required, ideal for a simple free project | Less officially stable than a paid search API; can occasionally be soft-rate-limited under heavy use |
| No persistent memory across queries | Keeps the system simple and predictable | The assistant cannot reference earlier questions in the same session |
| Reddit requires one manual setup step | Necessary since Reddit has no fully anonymous public API | Slightly higher setup friction than the other two sources |

---

## 9. Summary

The Terminal News Assistant demonstrates, in a deliberately simple and free-to-run form, the core mechanics of a Retrieval-Augmented Generation system: gathering live, multi-source information at query time, merging it into a unified context, and optionally letting a language model turn that context into a clear answer. Its layered architecture keeps each responsibility isolated and independently failable, which is what allows the system to remain useful and stable even when individual sources are unavailable or unconfigured — making it both a practical personal tool and an approachable example of applied RAG design.
