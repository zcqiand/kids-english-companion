/** 与后端 API 对齐的类型。 */
export interface Child {
  id: string;
  name: string;
  age: number;
  character_id: string;
  created_at?: string;
}

export interface Character {
  id: string;
  name_en: string;
  name_cn: string;
  emoji: string;
  color: string;
  greeting_en: string;
  greeting_cn: string;
  persona_en: string;
  style_cn: string;
  favorite_themes: string[];
}

export interface StorySummary {
  id: string;
  title_en: string;
  title_cn: string;
  character_id: string;
  theme: string;
  total_pages: number;
}

export interface StoryPage {
  en: string;
  cn: string;
  words: string[];
}

export interface WordCard {
  word_id: string;
  text: string;
  phonetic: string;
  meaning_cn: string;
  status: string;
}

export interface WordResult {
  word: string;
  ok: boolean;
  heard: string;
  status?: string;
}

export interface ReadalongNext {
  ok: boolean;
  story: StorySummary;
  page_index: number;
  page: StoryPage;
  due_words: string[];
}

export interface ReadalongResult {
  ok: boolean;
  sentence_en: string;
  sentence_cn: string;
  results: WordResult[];
  encouragement_en: string;
  encouragement_cn: string;
  tip_cn: string;
}

export interface PronunciationResult {
  ok: boolean;
  word: string;
  phonetic: string;
  meaning_cn: string;
  correct: boolean;
  heard: string;
  encouragement_en: string;
  encouragement_cn: string;
  tip_cn: string;
  status: string;
}
