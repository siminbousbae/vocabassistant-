-- =====================================================
-- AI Vocabulary Assistant - Database Schema
-- SQLite / PostgreSQL compatible
-- =====================================================

-- Users table (multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id VARCHAR(50) UNIQUE,
    username VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Words table (core vocabulary storage)
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- Core fields
    word VARCHAR(200) NOT NULL,
    phonetic VARCHAR(200),
    part_of_speech VARCHAR(100),
    chinese_meaning TEXT,

    -- Example from real sources
    example_sentence TEXT,
    chinese_translation TEXT,

    -- Source tracking
    source_name VARCHAR(200),
    source_url TEXT,

    -- Optional features
    audio_url TEXT,
    tags JSON,

    -- Extended info (auto-generated)
    collocations JSON,
    synonyms JSON,
    antonyms JSON,

    -- Learning metadata
    difficulty INTEGER DEFAULT 1,
    learned BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reviews table (Spaced Repetition SM-2)
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- SM-2 fields
    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_review_date TIMESTAMP,
    interval INTEGER DEFAULT 1,
    ease_factor REAL DEFAULT 2.5,
    repetitions INTEGER DEFAULT 0,
    quality INTEGER,

    -- Status
    is_due BOOLEAN DEFAULT TRUE,
    reviewed_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learning records (activity tracking)
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    action VARCHAR(50) NOT NULL,  -- added, reviewed, quizzed, audio_played
    score INTEGER,
    details JSON,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily statistics
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date VARCHAR(10) NOT NULL,  -- YYYY-MM-DD

    words_added INTEGER DEFAULT 0,
    words_reviewed INTEGER DEFAULT 0,
    words_learned INTEGER DEFAULT 0,
    quiz_score_avg REAL DEFAULT 0.0,
    study_minutes INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
CREATE INDEX IF NOT EXISTS idx_words_user ON words(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_word ON reviews(word_id);
CREATE INDEX IF NOT EXISTS idx_reviews_next ON reviews(next_review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_due ON reviews(is_due);
CREATE INDEX IF NOT EXISTS idx_records_word ON learning_records(word_id);
CREATE INDEX IF NOT EXISTS idx_records_action ON learning_records(action);
CREATE INDEX IF NOT EXISTS idx_stats_date ON daily_stats(date);
