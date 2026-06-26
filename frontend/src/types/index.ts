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

export interface ClaimVerdict {
  status: 'verified' | 'flagged';
  confidence: number;
  reason: string;
}

export interface Theme {
  theme: string;
  summary: string;
  source_indices: number[];
  verdict: ClaimVerdict;
}

export interface CompetitorActivity {
  competitor: string;
  activity: string;
  source_index: number;
  verdict: ClaimVerdict;
}

export interface HallucinationVerdict {
  overall_score: number;
  reasoning: string;
}

export interface Report {
  id: string;
  run_id: string;
  themes: Theme[];
  competitor_activities: CompetitorActivity[];
  source_urls: string[];
  hallucination_verdict: HallucinationVerdict;
  created_at: string;
}

export interface SSEEvent {
  type: 'progress' | 'complete' | 'error';
  step?: 'scraping' | 'analyzing' | 'judging';
  message?: string;
  run_id?: string;
}
