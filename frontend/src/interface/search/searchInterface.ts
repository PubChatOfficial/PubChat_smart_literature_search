export interface SearchSettings {
    max_refinement_attempts?: number;
    min_study_threshold?: number;
}

export interface SearchFilters {
    time?: string;
    author?: string;
    first_author?: string;
    last_author?: string;
    affiliation?: string;
    journal?: string;
    custom?: string;
}

export interface JournalFilters {
    impact_factor?: string;
    jcr_zone?: string;
    cas_zone?: string;
}

export interface LlmConfig {
    model?: string;
    api?: string[];
}

export interface SearchTaskRequest {
    user_query: string;
    outputlanguage?: string;
    search_settings?: SearchSettings;
    search_filters?: SearchFilters;
    journal_filters?: JournalFilters;
    llm_config?: LlmConfig;
}

export interface RetrievalItem {
    retrieval_title: string;
    retrieval_content: string;
}

export interface SearchProgress {
    current_round: number;
    current_round_retrieved_articles: number;
    total_selected_articles: number;
    total_retrieved_articles: number;
    max_round: number;
    auto_stop_articles: number;
}

export interface ArticleData {
    "no.": number;
    score: number | string;
    journal_name: string;
    article_title: string;
    publication_date: string;
    research_objective?: string;
    study_type?: string;
    research_method?: string;
    study_population?: string;
    main_results?: string;
    conclusions_and_significance?: string;
    highlights_and_innovations?: string;
    first_author?: string;
    corresponding_author?: string;
    first_author_affiliation?: string;
    issn?: string;
    jcr_partition?: string;
    video_path?: string;
    audio_path?: string;
    latest_if?: string;
    "5-year_if"?: string;
    ranking?: string;
    pmid?: string;
    pubmed_link?: string;
    pmc_link?: string;
    // Additional fields that might come from backend or usage
    impact_factor?: number | string;
    category_partition?: string;
    pubmed_id?: string;
    pmc_id?: string;
}

export interface SearchStatusResponse {
    search_status: string;
    download_link?: string;
    retrieval?: RetrievalItem[];
    search_progress?: SearchProgress;
    output_review?: ArticleData[];
}

export interface SearchDocument {
    id: string;
    task_id: string;
    size: number;
    user_query: string;
    created_time: string;
    download_link: string;
}