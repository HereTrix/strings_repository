export interface GlossaryTranslation {
  language_code: string
  preferred_translation: string
  updated_at: string
}

export interface GlossaryTerm {
  id: number
  term: string
  definition: string
  case_sensitive: boolean
  translations: GlossaryTranslation[]
  created_by: string
  created_at: string
  updated_at: string
}

export interface GlossarySuggestion {
  term: string
  definition: string
  translations: { language_code: string; preferred_translation: string }[]
  status: 'pending' | 'accepted' | 'rejected'
}

export interface GlossaryExtractionJob {
  id: number
  status: 'pending' | 'running' | 'complete' | 'failed'
  created_by: string
  created_at: string
  completed_at: string | null
  error_message: string
  suggestion_count: number
}

export interface GlossaryImportResult {
  imported: number
  updated: number
  skipped: number
  warnings: string[]
}
