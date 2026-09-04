# Enterprise AI & LLM Integration Protocol (`Iris ai`)

## Trigger
Activate when integrating or enhancing AI capabilities (LLM providers, Copilots, prompt engineering, vector search, or AI token billing). Command: `Iris ai`.

## 0. Skill Binding — Read Before Writing Any Line

The `claude-api` skill is the **source of truth** for model IDs, pricing, context
limits, streaming, tool use, prompt caching, and migration. Read it *before* opening
the target file — never answer from memory, and never let a model ID or price
reach {USER_NAME} without it.

**Mandatory** when the work names Claude/Anthropic in any form (`claude-*`,
`@anthropic-ai`, Opus/Sonnet/Haiku/Fable), when {USER_NAME} asks any LLM question, or
when the task is LLM-shaped with the provider unstated (agent, RAG, LLM-judge,
tool definitions, debugging refusals or truncation).

**Skip only** when a different provider is the subject — OpenAI, Gemini, Llama,
Mistral, Cohere, Ollama. If no provider is named, grep the project first rather than
reading the file blind.

This protocol deliberately carries **no model table**. A hardcoded model list is an
anti-pattern: it is stale the week it is written, and a stale ID ships as a runtime
404. The skill is versioned by the host; this file is not.

## 1. Multi-Provider Fallback & Resilience
- **Provider Abstraction**: Never bind business logic directly to a single SDK. Pass through unified provider interface (`OpenAI`, `AzureOpenAI`, `Anthropic`, `Gemini`).
- **Graceful Fallback**: Configure multi-provider failover chains (Primary → Secondary → Tertiary) on API timeouts or quota exhaustion.

## 2. Prompt Security & Input Hygiene
- **Prompt Injection Defense**: Sanitize user-provided text, contact fields, and KB context before embedding into system/user prompt templates.
- **System Prompt Integrity**: Keep system instructions immutable and separated from untrusted external inputs.

## 3. Token Governance & Metering
- **Token Tracking**: Record precise token usage (`prompt_tokens`, `completion_tokens`, `total_cost`) per tenant, user, and module invocation.
- **Response Validation**: Parse LLM responses into strict JSON schemas with fallback defaults for malformed model output.
