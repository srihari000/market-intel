export interface Run {
  id: string;
  title: string;
  competitors: string[];
  topics: string[];
  source_urls: string[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface Theme {
  theme: string;
  summary: string;
  source_indices: number[];
}

export interface CompetitorActivity {
  competitor: string;
  activity: string;
  source_index: number;
}

export interface FlaggedClaim {
  claim: string;
  reason: string;
}

export interface HallucinationVerdict {
  score: number;
  flagged_claims: FlaggedClaim[];
  reasoning: string;
}

export interface Report {
  id: string;
  run_id: string;
  themes: Theme[];
  competitor_activities: CompetitorActivity[];
  raw_sources: Record<string, string>;
  hallucination_verdict: HallucinationVerdict;
  created_at: string;
}

export interface SSEEvent {
  type: 'progress' | 'complete' | 'error';
  step?: 'scraping' | 'analyzing' | 'judging';
  message?: string;
  run_id?: string;
}
