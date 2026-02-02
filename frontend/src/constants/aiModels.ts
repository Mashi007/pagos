/**
 * Modelos OpenRouter recomendados (buen balance costo/calidad).
 * Ref: https://openrouter.ai/docs/guides/overview/models
 */
export const OPENROUTER_MODELS = [
  { id: 'openai/gpt-4o-mini', label: 'GPT-4o Mini (OpenAI) — Recomendado, económico' },
  { id: 'openai/gpt-4o', label: 'GPT-4o (OpenAI) — Más capaz' },
  { id: 'google/gemini-2.0-flash-001', label: 'Gemini 2.0 Flash (Google) — Rápido y barato' },
  { id: 'anthropic/claude-3-5-haiku', label: 'Claude 3.5 Haiku (Anthropic) — Buen balance' },
  { id: 'anthropic/claude-3-5-sonnet', label: 'Claude 3.5 Sonnet (Anthropic) — Más preciso' },
  { id: 'meta-llama/llama-3.1-70b-instruct', label: 'Llama 3.1 70B (Meta) — Open source' },
] as const
