// ==========================================
// VocabAI — Frontend (VIP Edition)
// ==========================================

// State
let words = [];
let reviewQueue = [];
let reviewIndex = 0;
let currentReviewWord = null;
let isReviewRevealed = false;
let reviewedCount = 0;
let quizQueue = [];
let quizIndex = 0;
let quizScore = 0;
let currentQuizQuestion = null;
let currentTab = 'learn';
let currentFilter = 'all';
let wordSearchQuery = '';
let addedDateFilter = '';
let statsPeriod = 'day';
let latestStatsPayload = null;

// DOM Elements
const tabs = {
    learn: document.getElementById('tab-learn'),
    review: document.getElementById('tab-review'),
    quiz: document.getElementById('tab-quiz'),
    stats: document.getElementById('tab-stats')
};

const navButtons = {
    learn: document.querySelector('[data-tab="learn"]'),
    review: document.querySelector('[data-tab="review"]'),
    quiz: document.querySelector('[data-tab="quiz"]'),
    stats: document.querySelector('[data-tab="stats"]')
};

// ==========================================
// UTILITY
// ==========================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function showLoading(message = 'Loading...') {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.remove('hidden');
        loading.querySelector('p').textContent = message;
    }
}

function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.add('hidden');
    }
}

// ==========================================
// TAB NAVIGATION
// ==========================================

function switchTab(tabName) {
    Object.keys(tabs).forEach(key => {
        if (tabs[key]) {
            tabs[key].classList.toggle('active', key === tabName);
        }
    });

    Object.keys(navButtons).forEach(key => {
        if (navButtons[key]) {
            navButtons[key].classList.toggle('active', key === tabName);
        }
    });

    currentTab = tabName;

    if (tabName === 'learn') loadWords();
    if (tabName === 'review') loadReviewTab();
    if (tabName === 'quiz') loadQuizTab();
    if (tabName === 'stats') loadStats();
}

// ==========================================
// WORDS TAB (Learn)
// ==========================================

async function loadWords() {
    try {
        const response = await fetch('/words/list');
        if (!response.ok) throw new Error('Failed to load words');
        words = await response.json();
        renderWords();
        updateHeaderStats();
    } catch (error) {
        showToast('Failed to load words', 'error');
        console.error(error);
    }
}

function updateHeaderStats() {
    const wordCount = document.getElementById('word-count');
    if (wordCount) {
        wordCount.textContent = words.length;
    }
}

function renderWords() {
    const container = document.getElementById('words-grid');
    const emptyState = document.getElementById('empty-words');

    if (!container) {
        console.error('ERROR: words-grid container not found!');
        return;
    }

    let filteredWords = words;
    if (currentFilter === 'due') {
        filteredWords = words.filter(w => w.is_due);
    } else if (currentFilter === 'learned') {
        filteredWords = words.filter(w => w.learned);
    }

    if (wordSearchQuery) {
        const query = wordSearchQuery.toLowerCase();
        filteredWords = filteredWords.filter(word => {
            return [
                word.word,
                word.phonetic,
                word.part_of_speech,
                word.chinese_meaning,
                word.example_sentence,
                word.source_name
            ].some(value => (value || '').toLowerCase().includes(query));
        });
    }

    if (addedDateFilter) {
        filteredWords = filteredWords.filter(word => {
            return (word.created_at || '').slice(0, 10) === addedDateFilter;
        });
    }

    if (filteredWords.length === 0) {
        container.innerHTML = '';
        if (emptyState) {
            emptyState.classList.remove('hidden');
            const emptyMsg = emptyState.querySelector('p');
            if (emptyMsg) {
                if (addedDateFilter) {
                    emptyMsg.textContent = `No words added on ${addedDateFilter}.`;
                } else if (wordSearchQuery) {
                    emptyMsg.textContent = `No words found for "${wordSearchQuery}".`;
                } else if (currentFilter === 'due') {
                    emptyMsg.textContent = 'No words due for review. Great job!';
                } else if (currentFilter === 'learned') {
                    emptyMsg.textContent = 'No learned words yet. Keep reviewing!';
                } else {
                    emptyMsg.textContent = 'No words yet. Add your first word above!';
                }
            }
        }
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    container.innerHTML = filteredWords.map(word => `
        <div class="word-card ${word.learned ? 'learned' : ''} ${word.is_due ? 'due' : ''}" data-word-id="${word.id}">
            <div class="word-header">
                <div>
                    <div class="word-title">${word.word}</div>
                    <div class="word-phonetic">${word.phonetic || ''}</div>
                </div>
                <span class="word-pos">${word.part_of_speech || 'N/A'}</span>
            </div>
            <div class="word-meaning">${word.chinese_meaning || 'No meaning yet'}</div>
            ${word.example_sentence ? `
                <div class="word-example">${word.example_sentence}</div>
            ` : ''}
            ${word.source_url ? `
                <div class="word-source">
                    <i class="fas fa-link"></i>
                    <a href="${word.source_url}" target="_blank" rel="noopener noreferrer">
                        ${word.source_name || 'Open source'}
                    </a>
                </div>
            ` : ''}
            <div class="word-actions">
                <button class="btn-audio-word" data-word-id="${word.id}" title="Play pronunciation" aria-label="Play pronunciation for ${word.word}">
                    <i class="fas fa-volume-up"></i> Listen
                </button>
                <button class="btn-review-word" data-word-id="${word.id}">
                    <i class="fas fa-brain"></i> Review
                </button>
                <button class="btn-detail-word" data-word-id="${word.id}">
                    <i class="fas fa-info-circle"></i> Details
                </button>
                <button class="btn-delete-word" data-word-id="${word.id}">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');

    attachWordCardListeners();
}

function attachWordCardListeners() {
    document.querySelectorAll('.btn-audio-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            const word = words.find(w => w.id === wordId);
            if (word) speakEnglish(word.word);
        });
    });

    document.querySelectorAll('.btn-review-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            startSingleWordReview(wordId);
        });
    });

    document.querySelectorAll('.btn-detail-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            showWordDetail(wordId);
        });
    });

    document.querySelectorAll('.btn-delete-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            deleteWord(wordId);
        });
    });
}

// ==========================================
// REVIEW — Flashcard Logic
// ==========================================

function resetReviewState() {
    reviewQueue = [];
    reviewIndex = 0;
    currentReviewWord = null;
    isReviewRevealed = false;
    reviewedCount = 0;
}

async function loadReviewTab() {
    const header = document.getElementById('review-mode-header');
    const controls = document.getElementById('review-controls');
    const progressContainer = document.getElementById('review-progress-container');
    const statsRow = document.getElementById('review-stats-row');
    const flashcard = document.getElementById('flashcard-container');
    const emptyReview = document.getElementById('empty-review');

    try {
        const response = await fetch('/review/due');
        if (!response.ok) throw new Error('Failed to load due words');
        const data = await response.json();

        const dueWords = data.due_words || [];

        const badge = document.getElementById('review-badge');
        if (badge) badge.textContent = dueWords.length;

        if (dueWords.length === 0) {
            header?.classList.add('hidden');
            controls?.classList.add('hidden');
            progressContainer?.classList.add('hidden');
            statsRow?.classList.add('hidden');
            flashcard?.classList.add('hidden');
            emptyReview?.classList.remove('hidden');
            return;
        }

        emptyReview?.classList.add('hidden');
        header?.classList.remove('hidden');
        controls?.classList.remove('hidden');
        progressContainer?.classList.remove('hidden');
        statsRow?.classList.remove('hidden');
        flashcard?.classList.remove('hidden');

        startReviewSession(dueWords);

    } catch (error) {
        showToast('Failed to load review', 'error');
        console.error(error);
    }
}

function startReviewSession(dueWords) {
    resetReviewState();
    reviewQueue = [...dueWords];
    reviewIndex = 0;
    reviewedCount = 0;
    updateReviewStats();
    renderFlashcard();
}

function updateReviewStats() {
    const total = reviewQueue.length;
    const current = total > 0 ? reviewIndex + 1 : 0;
    const remaining = total - reviewedCount;

    document.getElementById('review-current').textContent = current;
    document.getElementById('review-total').textContent = total;
    document.getElementById('stat-reviewed-count').textContent = reviewedCount;
    document.getElementById('stat-remaining-count').textContent = remaining;

    const bar = document.getElementById('review-progress-bar');
    if (bar && total > 0) {
        const pct = ((reviewIndex) / total) * 100;
        bar.style.width = `${pct}%`;
    }
}

function renderFlashcard() {
    if (reviewIndex >= reviewQueue.length) {
        showReviewComplete();
        return;
    }

    currentReviewWord = reviewQueue[reviewIndex];
    isReviewRevealed = false;

    document.getElementById('flashcard-word').textContent = currentReviewWord.word;
    document.getElementById('flashcard-meta').textContent =
        `${currentReviewWord.phonetic || ''} · ${currentReviewWord.part_of_speech || 'noun'}`;

    document.getElementById('flashcard-meaning').textContent =
        currentReviewWord.chinese_meaning || 'No meaning yet';
    document.getElementById('flashcard-example').textContent =
        currentReviewWord.example_sentence || '';
    document.getElementById('flashcard-translation').textContent =
        currentReviewWord.chinese_translation || '';

    document.getElementById('flashcard-back').classList.add('hidden');
    document.getElementById('btn-show-answer').classList.remove('hidden');

    updateReviewStats();
}

function showAnswer() {
    if (!currentReviewWord) return;
    isReviewRevealed = true;
    document.getElementById('flashcard-back').classList.remove('hidden');
    document.getElementById('btn-show-answer').classList.add('hidden');
}

function prevCard() {
    if (reviewIndex > 0) {
        reviewIndex--;
        renderFlashcard();
    }
}

function nextCard() {
    if (reviewIndex < reviewQueue.length - 1) {
        reviewIndex++;
        renderFlashcard();
    }
}

async function markAsReviewed() {
    if (!currentReviewWord) return;

    const quality = 3;

    try {
        const response = await fetch('/review/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: currentReviewWord.word_id,
                quality: quality
            })
        });

        if (!response.ok) throw new Error('Failed to submit review');

        reviewedCount++;
        showToast(`Reviewed: ${currentReviewWord.word}`, 'success');

        const wordIdx = words.findIndex(w => w.id === currentReviewWord.word_id);
        if (wordIdx !== -1) words[wordIdx].is_due = false;

        reviewIndex++;
        renderFlashcard();

    } catch (error) {
        showToast('Failed to submit review', 'error');
        console.error(error);
    }
}

function shuffleCards() {
    if (reviewQueue.length < 2) return;
    for (let i = reviewQueue.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [reviewQueue[i], reviewQueue[j]] = [reviewQueue[j], reviewQueue[i]];
    }
    reviewIndex = 0;
    showToast('Cards shuffled', 'success');
    renderFlashcard();
}

function resetReviewSession() {
    if (reviewQueue.length === 0) {
        loadReviewTab();
        return;
    }
    reviewIndex = 0;
    reviewedCount = 0;
    isReviewRevealed = false;
    showToast('Review session reset', 'info');
    renderFlashcard();
}

function showReviewComplete() {
    const container = document.getElementById('flashcard-container');
    if (container) {
        container.innerHTML = `
            <div class="review-complete">
                <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
                <h2>Review Complete!</h2>
                <p>You reviewed ${reviewedCount} words in this session.</p>
                <button class="btn-primary" onclick="loadReviewTab()">Review Again</button>
                <button class="btn-secondary" onclick="switchTab('learn')" style="margin-left:10px">Back to Words</button>
            </div>
        `;
    }
    loadWords();
}

async function startSingleWordReview(wordId) {
    resetReviewState();
    switchTab('review');

    const container = document.getElementById('flashcard-container');
    if (!container) return;

    showLoading('Loading word...');

    try {
        const response = await fetch(`/review/word/${wordId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load word');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || 'Failed to load word');
        }

        reviewQueue = [{
            word_id: data.word_id,
            word: data.word,
            phonetic: data.phonetic,
            chinese_meaning: data.chinese_meaning,
            example_sentence: data.example_sentence,
            chinese_translation: data.chinese_translation,
            part_of_speech: data.part_of_speech
        }];
        reviewIndex = 0;

        hideLoading();
        renderFlashcard();

    } catch (error) {
        hideLoading();
        showToast(error.message, 'error');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>❌ ${error.message}</p>
                    <button class="btn-primary" onclick="switchTab('learn')">Back to Words</button>
                </div>
            `;
        }
    }
}

// TTS Helpers
function speakEnglish(text) {
    if (!text) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-US';
    speechSynthesis.speak(u);
}

function speakChinese(text) {
    if (!text) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'zh-CN';
    speechSynthesis.speak(u);
}

// ==========================================
// ADD WORD
// ==========================================

async function addWord() {
    const input = document.getElementById('word-input');
    const word = input?.value.trim();

    if (!word) {
        showToast('Please enter a word', 'error');
        return;
    }

    showLoading('Searching real news sources...');

    try {
        const response = await fetch('/words/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add word');
        }

        const result = await response.json();
        showToast(`Added: ${result.word.word || word}`, 'success');

        if (input) input.value = '';
        loadWords();

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ==========================================
// WORD DETAIL MODAL
// ==========================================

function showWordDetail(wordId) {
    const word = words.find(w => w.id === wordId);
    if (!word) return;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>${word.word.toUpperCase()}</h3>
                <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <p><strong>Phonetic:</strong> ${word.phonetic || 'N/A'}</p>
                <p><strong>POS:</strong> ${word.part_of_speech || 'N/A'}</p>
                <p><strong>Meaning:</strong> ${word.chinese_meaning || 'N/A'}</p>
                <hr>
                <p><strong>Example:</strong></p>
                <p class="word-example">${word.example_sentence || 'N/A'}</p>
                <p>${word.chinese_translation || ''}</p>
                <hr>
                <p><strong>Source:</strong> ${
                    word.source_url
                        ? `<a href="${word.source_url}" target="_blank" rel="noopener noreferrer">${word.source_name || word.source_url}</a>`
                        : (word.source_name || 'N/A')
                }</p>
                ${word.collocations ? `<p><strong>Collocations:</strong> ${word.collocations.join(', ')}</p>` : ''}
                ${word.synonyms ? `<p><strong>Synonyms:</strong> ${word.synonyms.join(', ')}</p>` : ''}
                ${word.antonyms ? `<p><strong>Antonyms:</strong> ${word.antonyms.join(', ')}</p>` : ''}
            </div>
            <div class="modal-footer">
                <button class="btn-primary btn-review-modal" data-word-id="${word.id}"><i class="fas fa-brain"></i> Review</button>
                <button class="btn-secondary modal-close-btn">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-close-btn').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    modal.querySelector('.btn-review-modal').addEventListener('click', () => {
        modal.remove();
        startSingleWordReview(word.id);
    });
}

// ==========================================
// DELETE WORD
// ==========================================

async function deleteWord(wordId) {
    if (!confirm('Are you sure you want to delete this word?')) return;

    try {
        const response = await fetch(`/words/delete/${wordId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete');

        showToast('Word deleted', 'success');
        loadWords();

    } catch (error) {
        showToast('Failed to delete word', 'error');
    }
}

// ==========================================
// QUIZ
// ==========================================

async function loadQuizTab() {
    const container = document.getElementById('quiz-container');
    if (!container) return;

    try {
        const response = await fetch('/review/quiz');
        if (!response.ok) throw new Error('Failed to load quiz');
        const data = await response.json();

        quizQueue = data.quiz || [];
        quizIndex = 0;
        quizScore = 0;

        if (quizQueue.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No quiz available. Add more words first!</p>
                </div>
            `;
            return;
        }

        showNextQuizQuestion();

    } catch (error) {
        showToast('Failed to load quiz', 'error');
    }
}

function showNextQuizQuestion() {
    const container = document.getElementById('quiz-container');
    if (!container) return;

    if (quizIndex >= quizQueue.length) {
        const percentage = quizQueue.length > 0 ? Math.round((quizScore / quizQueue.length) * 100) : 0;
        container.innerHTML = `
            <div class="quiz-results">
                <div class="results-icon">🎉</div>
                <h2>Quiz Complete!</h2>
                <div class="score-display">${quizScore}/${quizQueue.length} (${percentage}%)</div>
                <p>${percentage >= 80 ? '🎉 Excellent!' : percentage >= 60 ? '👍 Good job!' : '💪 Keep practicing!'}</p>
                <button class="btn-primary" onclick="loadQuizTab()">Try Again</button>
            </div>
        `;
        return;
    }

    currentQuizQuestion = quizQueue[quizIndex];

    container.innerHTML = `
        <div class="quiz-progress">
            <span>Question ${quizIndex + 1}/${quizQueue.length}</span>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${(quizIndex / quizQueue.length) * 100}%"></div>
            </div>
        </div>
        <div class="quiz-question">${currentQuizQuestion.question}</div>
        <div class="quiz-options">
            ${currentQuizQuestion.options.map((opt, i) => `
                <button class="quiz-option" data-index="${i}">
                    <span class="option-letter">${String.fromCharCode(65 + i)}</span>
                    <span>${opt}</span>
                </button>
            `).join('')}
        </div>
    `;

    document.querySelectorAll('.quiz-option').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const selectedIndex = parseInt(e.currentTarget.dataset.index);
            submitQuizAnswer(selectedIndex);
        });
    });
}

async function submitQuizAnswer(selectedIndex) {
    if (!currentQuizQuestion) return;

    const isCorrect = selectedIndex === currentQuizQuestion.correct_index;

    if (isCorrect) quizScore++;

    const options = document.querySelectorAll('.quiz-option');
    options.forEach((btn, i) => {
        btn.disabled = true;
        if (i === currentQuizQuestion.correct_index) {
            btn.classList.add('correct');
        } else if (i === selectedIndex && !isCorrect) {
            btn.classList.add('wrong');
        }
    });

    try {
        await fetch('/review/quiz/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: currentQuizQuestion.word_id,
                selected_index: selectedIndex,
                correct_index: currentQuizQuestion.correct_index
            })
        });
    } catch (error) {
        console.error('Failed to update review:', error);
    }

    setTimeout(() => {
        quizIndex++;
        showNextQuizQuestion();
    }, 1500);
}

// ==========================================
// STATS
// ==========================================

async function loadStats() {
    try {
        const [overview, wordsData, reviews, daily] = await Promise.all([
            fetch('/stats/overview').then(r => r.json()),
            fetch('/stats/words').then(r => r.json()),
            fetch('/stats/reviews').then(r => r.json()),
            fetch('/stats/daily?days=365').then(r => r.json())
        ]);

        latestStatsPayload = { overview, wordsData, reviews, daily };
        renderStats(overview, wordsData, reviews, daily);

    } catch (error) {
        showToast('Failed to load stats', 'error');
    }
}

function renderStats(overview, wordsData, reviews, daily) {
    const stats = overview.stats || {};
    const learningRate = wordsData.learning_rate || 0;

    document.getElementById('stat-total').textContent = wordsData.total_words || 0;
    document.getElementById('stat-learned').textContent = wordsData.learned_words || 0;
    document.getElementById('stat-reviewed').textContent = reviews.weekly_reviews || 0;
    document.getElementById('stat-streak').textContent = stats.current_streak || 0;

    const masteryText = document.getElementById('mastery-text');
    if (masteryText) masteryText.textContent = stats.mastery_level || 'Novice';

    const masteryFill = document.getElementById('mastery-progress-fill');
    if (masteryFill) masteryFill.style.width = `${Math.min(100, learningRate)}%`;

    const masteryCaption = document.getElementById('mastery-caption');
    if (masteryCaption) masteryCaption.textContent = `${learningRate}% learned (${wordsData.learned_words || 0}/${wordsData.total_words || 0})`;

    const dailyRows = normalizeDailyRows(daily.daily_data || []);
    const periodData = buildStatsSeries(dailyRows, statsPeriod);
    renderActivityChart(periodData);
    renderPeriodDetails(periodData);
    renderDifficultyChart(wordsData.by_difficulty || {});
}

function normalizeDailyRows(rows) {
    return rows.map(row => ({
        date: row.date,
        words_added: Number(row.words_added || 0),
        words_reviewed: Number(row.words_reviewed || 0),
        words_learned: Number(row.words_learned || 0),
        quiz_score_avg: Number(row.quiz_score_avg || 0),
        study_minutes: Number(row.study_minutes || 0)
    }));
}

function formatDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function addDays(date, days) {
    const next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
}

function startOfWeek(date) {
    const next = new Date(date);
    const day = next.getDay() || 7;
    next.setHours(0, 0, 0, 0);
    next.setDate(next.getDate() - day + 1);
    return next;
}

function sumRows(rows) {
    return rows.reduce((acc, row) => {
        acc.added += row.words_added;
        acc.reviewed += row.words_reviewed;
        acc.learned += row.words_learned;
        if (row.words_added || row.words_reviewed || row.words_learned) acc.activeDays += 1;
        return acc;
    }, { added: 0, reviewed: 0, learned: 0, activeDays: 0 });
}

function rowsBetween(rows, start, end) {
    const startKey = formatDateKey(start);
    const endKey = formatDateKey(end);
    return rows.filter(row => row.date >= startKey && row.date <= endKey);
}

function buildStatsSeries(rows, period) {
    const now = new Date();
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    if (period === 'day') {
        const series = [];
        for (let offset = 6; offset >= 0; offset--) {
            const date = addDays(now, -offset);
            const key = formatDateKey(date);
            const row = rows.find(item => item.date === key);
            series.push({
                label: date.toLocaleDateString(undefined, { weekday: 'short' }),
                range: key,
                added: row?.words_added || 0,
                reviewed: row?.words_reviewed || 0,
                learned: row?.words_learned || 0,
                activeDays: row && (row.words_added || row.words_reviewed || row.words_learned) ? 1 : 0
            });
        }
        return {
            period,
            title: 'Daily Activity',
            subtitle: 'Last 7 days of vocabulary work.',
            label: 'Last 7 days',
            series
        };
    }

    if (period === 'week') {
        const currentWeek = startOfWeek(now);
        const series = [];
        for (let offset = 7; offset >= 0; offset--) {
            const start = addDays(currentWeek, -offset * 7);
            const end = addDays(start, 6);
            const summary = sumRows(rowsBetween(rows, start, end));
            series.push({
                label: `${monthNames[start.getMonth()]} ${start.getDate()}`,
                range: `${formatDateKey(start)} - ${formatDateKey(end)}`,
                ...summary
            });
        }
        return {
            period,
            title: 'Weekly Activity',
            subtitle: 'Last 8 weeks grouped by review week.',
            label: 'Last 8 weeks',
            series
        };
    }

    if (period === 'month') {
        const series = [];
        for (let offset = 11; offset >= 0; offset--) {
            const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
            const start = new Date(date.getFullYear(), date.getMonth(), 1);
            const end = new Date(date.getFullYear(), date.getMonth() + 1, 0);
            const summary = sumRows(rowsBetween(rows, start, end));
            series.push({
                label: `${monthNames[start.getMonth()]}`,
                range: `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}`,
                ...summary
            });
        }
        return {
            period,
            title: 'Monthly Activity',
            subtitle: 'Last 12 months grouped by calendar month.',
            label: 'Last 12 months',
            series
        };
    }

    const series = [];
    for (let offset = 4; offset >= 0; offset--) {
        const year = now.getFullYear() - offset;
        const start = new Date(year, 0, 1);
        const end = new Date(year, 11, 31);
        const summary = sumRows(rowsBetween(rows, start, end));
        series.push({
            label: String(year),
            range: String(year),
            ...summary
        });
    }
    return {
        period,
        title: 'Yearly Activity',
        subtitle: 'Last 5 years grouped by calendar year.',
        label: 'Last 5 years',
        series
    };
}

function renderActivityChart(periodData) {
    const title = document.getElementById('activity-title');
    const subtitle = document.getElementById('activity-subtitle');
    const chart = document.getElementById('activity-chart');
    if (!chart) return;

    if (title) title.innerHTML = `<i class="fas fa-chart-column"></i> ${periodData.title}`;
    if (subtitle) subtitle.textContent = periodData.subtitle;

    const totals = periodData.series.reduce((acc, item) => {
        acc.added += item.added;
        acc.reviewed += item.reviewed;
        acc.learned += item.learned;
        acc.activeDays += item.activeDays;
        return acc;
    }, { added: 0, reviewed: 0, learned: 0, activeDays: 0 });

    const periodTotal = document.getElementById('period-total-value');
    if (periodTotal) periodTotal.textContent = totals.reviewed;

    const maxValue = Math.max(
        1,
        ...periodData.series.flatMap(item => [item.added, item.reviewed, item.learned])
    );

    chart.innerHTML = `
        ${periodData.series.map(item => `
            <div class="activity-bar-group" title="${item.range}">
                <div class="activity-bar added" style="height: ${(item.added / maxValue) * 100}%"></div>
                <div class="activity-bar reviewed" style="height: ${(item.reviewed / maxValue) * 100}%"></div>
                <div class="activity-bar learned" style="height: ${(item.learned / maxValue) * 100}%"></div>
                <div class="activity-label">${item.label}</div>
            </div>
        `).join('')}
        <div class="chart-legend">
            <span><i class="legend-added"></i> Added</span>
            <span><i class="legend-reviewed"></i> Reviewed</span>
            <span><i class="legend-learned"></i> Learned</span>
        </div>
    `;

    chart.dataset.totals = JSON.stringify(totals);
}

function renderPeriodDetails(periodData) {
    const totals = periodData.series.reduce((acc, item) => {
        acc.added += item.added;
        acc.reviewed += item.reviewed;
        acc.learned += item.learned;
        acc.activeDays += item.activeDays;
        return acc;
    }, { added: 0, reviewed: 0, learned: 0, activeDays: 0 });

    const label = document.getElementById('period-label');
    if (label) label.textContent = periodData.label;

    document.getElementById('period-added').textContent = totals.added;
    document.getElementById('period-reviewed').textContent = totals.reviewed;
    document.getElementById('period-learned').textContent = totals.learned;
    document.getElementById('period-active-days').textContent = totals.activeDays;
}

function renderDifficultyChart(byDifficulty) {
    const chart = document.getElementById('difficulty-chart');
    if (!chart) return;

    const levels = [1, 2, 3, 4, 5].map(level => ({
        level,
        count: Number(byDifficulty[`level_${level}`] || 0)
    }));
    const maxCount = Math.max(1, ...levels.map(item => item.count));

    chart.innerHTML = levels.map(item => `
        <div class="difficulty-row">
            <small>Level ${item.level}</small>
            <div class="difficulty-track">
                <div class="difficulty-fill" style="width: ${(item.count / maxCount) * 100}%"></div>
            </div>
            <small>${item.count}</small>
        </div>
    `).join('');
}

function setStatsPeriod(period) {
    statsPeriod = period;
    document.querySelectorAll('.stats-period').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });
    if (latestStatsPayload) {
        renderStats(
            latestStatsPayload.overview,
            latestStatsPayload.wordsData,
            latestStatsPayload.reviews,
            latestStatsPayload.daily
        );
    }
}

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            if (tabName) switchTab(tabName);
        });
    });

    // Add word button
    const addBtn = document.getElementById('add-btn');
    if (addBtn) {
        addBtn.addEventListener('click', addWord);
    }

    // Enter key on input
    const wordInput = document.getElementById('word-input');
    if (wordInput) {
        wordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addWord();
        });
    }

    // Filter buttons
    const filterAll = document.getElementById('filter-all');
    const filterDue = document.getElementById('filter-due');
    const filterLearned = document.getElementById('filter-learned');

    [filterAll, filterDue, filterLearned].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', (e) => {
                [filterAll, filterDue, filterLearned].forEach(b => b?.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.id.replace('filter-', '');
                renderWords();
            });
        }
    });

    const collectionSearch = document.getElementById('collection-search');
    if (collectionSearch) {
        collectionSearch.addEventListener('input', (e) => {
            wordSearchQuery = e.target.value.trim();
            renderWords();
        });
    }

    const addedDateInput = document.getElementById('added-date-filter');
    const clearDateBtn = document.getElementById('clear-date-filter');
    if (addedDateInput) {
        addedDateInput.addEventListener('change', (e) => {
            addedDateFilter = e.target.value;
            renderWords();
        });
    }
    if (clearDateBtn) {
        clearDateBtn.addEventListener('click', () => {
            addedDateFilter = '';
            if (addedDateInput) addedDateInput.value = '';
            renderWords();
        });
    }

    document.querySelectorAll('.stats-period').forEach(btn => {
        btn.addEventListener('click', () => {
            setStatsPeriod(btn.dataset.period);
        });
    });

    // Review flashcard controls
    document.getElementById('btn-show-answer')?.addEventListener('click', showAnswer);
    document.getElementById('btn-prev-card')?.addEventListener('click', prevCard);
    document.getElementById('btn-next-card')?.addEventListener('click', nextCard);
    document.getElementById('btn-mark-reviewed')?.addEventListener('click', markAsReviewed);
    document.getElementById('btn-shuffle')?.addEventListener('click', shuffleCards);
    document.getElementById('btn-reset-review')?.addEventListener('click', resetReviewSession);

    // Audio TTS
    document.getElementById('btn-audio-en')?.addEventListener('click', () => {
        if (currentReviewWord) speakEnglish(currentReviewWord.word);
    });
    document.getElementById('btn-audio-cn')?.addEventListener('click', () => {
        if (currentReviewWord) speakChinese(currentReviewWord.chinese_meaning);
    });

    // Load initial data
    loadWords();

    // Switch to default tab
    switchTab('learn');
});
