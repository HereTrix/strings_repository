export interface TMSuggestion {
  token_key: string
  source_text: string
  translation_text: string
  similarity_score: number   // 0.0–1.0
}
