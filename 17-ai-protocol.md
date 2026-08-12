# Enterprise AI & LLM Integration Protocol (`Iris ai`)

## Trigger
Activate when integrating or enhancing AI capabilities (LLM providers, Copilots, prompt engineering, vector search, or AI token billing). Command: `Iris ai`.

## 1. Multi-Provider Fallback & Resilience
- **Provider Abstraction**: Never bind business logic directly to a single SDK. Pass through unified provider interface (`OpenAI`, `AzureOpenAI`, `Anthropic`, `Gemini`).
- **Graceful Fallback**: Configure multi-provider failover chains (Primary → Secondary → Tertiary) on API timeouts or quota exhaustion.

## 2. Prompt Security & Input Hygiene
- **Prompt Injection Defense**: Sanitize user-provided text, contact fields, and KB context before embedding into system/user prompt templates.
- **System Prompt Integrity**: Keep system instructions immutable and separated from untrusted external inputs.

## 3. Token Governance & Metering
- **Token Tracking**: Record precise token usage (`prompt_tokens`, `completion_tokens`, `total_cost`) per tenant, user, and module invocation.
- **Response Validation**: Parse LLM responses into strict JSON schemas with fallback defaults for malformed model output.
