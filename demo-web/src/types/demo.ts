export type QuestionChoice = {
  key: string;
  label: string;
};

export type Question = {
  index: number;
  id: string;
  text: string;
  choices: QuestionChoice[];
};

export type Recommendation = {
  model: string;
  score: number;
  reason: string;
  archetype: string;
  similar_consumers?: string[];
  quick_grade?: string;
  fuel_type?: string;
  seating_capacity?: number;
  appeal_points?: string[];
};

export type ExcludedModel = {
  model: string;
  reason: string;
};
