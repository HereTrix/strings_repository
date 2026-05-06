export type VerificationMode = 'source_quality' | 'translation_accuracy'
export type VerificationSeverity = 'ok' | 'warning' | 'error'
export type VerificationStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface VerificationSuggestion {
  token_id: number
  token_key: string
  language: string
  plural_form: string | null
  current: string
  suggestion: string
  severity: VerificationSeverity
  reason: string
}

export interface VerificationSummary {
  ok: number
  warning: number
  error: number
  total: number
}

export interface VerificationComment {
  id: number
  token_id: number
  token_key: string
  plural_form: string
  author: string
  text: string
  created_at: string
}

export interface VerificationResult {
  results: VerificationSuggestion[]
  summary: VerificationSummary
}

export interface VerificationReport {
  id: number
  mode: VerificationMode
  status: VerificationStatus
  target_language: string
  is_readonly: boolean
  string_count: number
  checks: string[]
  created_by: string
  created_at: string
  completed_at: string | null
  error_message?: string
  summary?: VerificationSummary
  result?: VerificationResult
  comments?: VerificationComment[]
}

export interface AIProvider {
  enabled: boolean
  provider_type?: 'openai' | 'anthropic'
  provider_label?: string
  endpoint_url?: string
  model_name?: string
  request_timeout?: number
  translation_instructions?: string
  verification_instructions?: string
  glossary_extraction_instructions?: string
  translation_memory_instructions?: string
  providers: { value: string; label: string }[]
}

export const MODE_CHECKS: Record<VerificationMode, { key: string; label: string }[]> = {
  source_quality: [
    { key: 'spelling_grammar', label: 'Spelling & Grammar' },
    { key: 'tone_register', label: 'Tone / Register' },
    { key: 'punctuation', label: 'Punctuation' },
    { key: 'capitalisation', label: 'Capitalisation' },
    { key: 'placeholder_format', label: 'Placeholder Format' },
  ],
  translation_accuracy: [
    { key: 'semantic_accuracy', label: 'Semantic Accuracy' },
    { key: 'placeholder_preservation', label: 'Placeholder Preservation' },
    { key: 'omissions_additions', label: 'Omissions / Additions' },
    { key: 'grammar_target', label: 'Grammar in Target Language' },
    { key: 'tone_match', label: 'Tone Match' },
    { key: 'glossary_compliance', label: 'Glossary Compliance' },
  ],
}
