// ========================================
// AI Vocabulary Assistant - Frontend
// Fixed Review Logic - Word Card Review Works Anytime
// ========================================

// State
let words = [];
let reviewQueue = [];
let reviewIndex = 0;
let currentReviewWord = null;
let isReviewRevealed = false;
let quizQueue = [];
let quizIndex = 0;
let quizScore = 0;
let currentQuizQuestion = null;
let currentTab = 'words';

// DOM Elements
const tabs = {
    words: document.getElementById('tab-words'),
    review: document.getElementById('tab-review'),
    quiz: document.getElementById('tab-quiz'),
    stats: document.getElementById('tab-stats')
};

const navButtons = {
    words: document.getElementById('nav-words'),
    review: document.getElementById('nav-review'),
    quiz: document.getElementById('nav-quiz'),
    stats: document.getElementById('nav-stats')
};

// ========================================
// UTILITY
// ========================================

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
    const existing = document.getElementById('loading-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.remove();
}

// ========================================
// TAB NAVIGATION
// ========================================

function switchTab(tabName) {
    // Update tab visibility
    Object.keys(tabs).forEach(key => {
        if (tabs[key]) {
            tabs[key].classList.toggle('active', key === tabName);
        }
    });

    // Update nav buttons
    Object.keys(navButtons).forEach(key => {
        if (navButtons[key]) {
            navButtons[key].classList.toggle('active', key === tabName);
        }
    });

    currentTab = tabName;

    // Refresh tab content
    if (tabName === 'words') loadWords();
    if (tabName === 'review') loadReviewTab();
    if (tabName === 'quiz') loadQuizTab();
    if (tabName === 'stats') loadStats();
}

// ========================================
// WORDS TAB
// ========================================

async function loadWords() {
    try {
        const response = await fetch('/api/words/list');
        if (!response.ok) throw new Error('Failed to load words');
        words = await response.json();
        renderWords();
    } catch (error) {
        showToast('Failed to load words', 'error');
        console.error(error);
    }
}

function renderWords() {
    const container = document.getElementById('words-list');
    if (!container) return;

    if (words.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No words yet. Add your first word above!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = words.map(word => `
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
            <div class="word-actions">
                <button class="btn-review-word" data-word-id="${word.id}">
                    🔄 Review
                </button>
                <button class="btn-detail-word" data-word-id="${word.id}">
                    📖 Details
                </button>
                <button class="btn-delete-word" data-word-id="${word.id}">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `).join('');

    // Attach event listeners
    attachWordCardListeners();
}

function attachWordCardListeners() {
    // Review button on word card - FIXED: Uses new endpoint
    document.querySelectorAll('.btn-review-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            startSingleWordReview(wordId);
        });
    });

    // Detail button
    document.querySelectorAll('.btn-detail-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            showWordDetail(wordId);
        });
    });

    // Delete button
    document.querySelectorAll('.btn-delete-word').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const wordId = parseInt(btn.dataset.wordId);
            deleteWord(wordId);
        });
    });
}

// ========================================
// REVIEW - THE FIXED PART
// ========================================

function resetReviewState() {
    reviewQueue = [];
    reviewIndex = 0;
    currentReviewWord = null;
    isReviewRevealed = false;
}

// Load review tab - shows due words list + start button
async function loadReviewTab() {
    const container = document.getElementById('review-container');
    if (!container) return;

    try {
        const response = await fetch('/api/review/due');
        if (!response.ok) throw new Error('Failed to load due words');
        const data = await response.json();

        const dueWords = data.due_words || [];

        if (dueWords.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No words due for review. Great job! 🎉</p>
                </div>
            `;
            return;
        }

        // Show due words list with start button
        container.innerHTML = `
            <div class="review-intro">
                <h3>📚 ${dueWords.length} words due for review</h3>
                <button id="btn-start-review" class="btn-primary">
                    🚀 Start Review Session
                </button>
            </div>
            <div class="due-words-preview">
                ${dueWords.map(w => `
                    <div class="due-word-item">
                        <span class="due-word-name">${w.word}</span>
                        <span class="due-word-meaning">${w.chinese_meaning || ''}</span>
                    </div>
                `).join('')}
            </div>
        `;

        // Attach start button listener
        const startBtn = document.getElementById('btn-start-review');
        if (startBtn) {
            startBtn.addEventListener('click', () => startReviewSession(dueWords));
        }

    } catch (error) {
        showToast('Failed to load review', 'error');
        console.error(error);
    }
}

// Start a full review session (from Review tab)
function startReviewSession(dueWords) {
    resetReviewState();
    reviewQueue = [...dueWords];
    reviewIndex = 0;
    showNextReviewWord();
}

// ========== FIXED: Word Card Review ==========
// Uses NEW endpoint: GET /api/review/word/{word_id}
// This works even if the word is NOT due!

async function startSingleWordReview(wordId) {
    resetReviewState();

    // Switch to review tab first
    switchTab('review');

    const container = document.getElementById('review-container');
    if (!container) return;

    showLoading('Loading word...');

    try {
        // NEW: Use the force-review endpoint
        const response = await fetch(`/api/review/word/${wordId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load word');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || 'Failed to load word');
        }

        // Create a single-word review queue
        reviewQueue = [{
            word_id: data.word_id,
            word: data.word,
            phonetic: data.phonetic,
            chinese_meaning: data.chinese_meaning,
            example_sentence: data.example_sentence,
            chinese_translation: data.chinese_translation
        }];
        reviewIndex = 0;

        hideLoading();
        showNextReviewWord();

    } catch (error) {
        hideLoading();
        showToast(error.message, 'error');
        console.error(error);

        // Show error in review tab
        container.innerHTML = `
            <div class="empty-state">
                <p>❌ ${error.message}</p>
                <button class="btn-primary" onclick="switchTab('words')">Back to Words</button>
            </div>
        `;
    }
}

function showNextReviewWord() {
    const container = document.getElementById('review-container');
    if (!container) return;

    // Check if review is complete
    if (reviewIndex >= reviewQueue.length) {
        container.innerHTML = `
            <div class="review-complete">
                <h2>🎉 Review Complete!</h2>
                <p>You reviewed ${reviewQueue.length} words.</p>
                <button id="btn-review-again" class="btn-primary">Review Again</button>
                <button id="btn-back-menu" class="btn-secondary">Back to Menu</button>
            </div>
        `;

        document.getElementById('btn-review-again')?.addEventListener('click', () => {
            resetReviewState();
            loadReviewTab();
        });

        document.getElementById('btn-back-menu')?.addEventListener('click', () => {
            switchTab('words');
        });

        return;
    }

    currentReviewWord = reviewQueue[reviewIndex];
    isReviewRevealed = false;

    container.innerHTML = `
        <div class="review-progress">
            <span>Word ${reviewIndex + 1} of ${reviewQueue.length}</span>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${(reviewIndex / reviewQueue.length) * 100}%"></div>
            </div>
        </div>
        <div class="review-card">
            <div class="review-word">
                <h3>${currentReviewWord.word}</h3>
                <div class="phonetic">${currentReviewWord.phonetic || ''}</div>
            </div>
            <div class="review-hidden" id="review-hidden-content" style="display: none;">
                <div class="review-meaning">
                    <p><strong>Meaning:</strong> ${currentReviewWord.chinese_meaning || 'N/A'}</p>
                    ${currentReviewWord.example_sentence ? `
                        <p class="example">${currentReviewWord.example_sentence}</p>
                        <p class="translation">${currentReviewWord.chinese_translation || ''}</p>
                    ` : ''}
                </div>
            </div>
            <button id="btn-reveal" class="btn-reveal">👁️ Reveal Answer</button>
            <div class="quality-buttons" id="quality-buttons" style="display: none;">
                <p>How well did you remember?</p>
                <div class="quality-row">
                    <button class="quality-btn q0" data-quality="0">😵 Again</button>
                    <button class="quality-btn q1" data-quality="1">😟 Hard</button>
                    <button class="quality-btn q2" data-quality="2">😐 Good</button>
                    <button class="quality-btn q3" data-quality="3">🙂 Easy</button>
                    <button class="quality-btn q4" data-quality="4">😊 Very Easy</button>
                    <button class="quality-btn q5" data-quality="5">🤩 Perfect</button>
                </div>
            </div>
        </div>
    `;

    // Attach reveal button listener
    const revealBtn = document.getElementById('btn-reveal');
    if (revealBtn) {
        revealBtn.addEventListener('click', revealReviewAnswer);
    }

    // Attach quality button listeners
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const quality = parseInt(e.target.dataset.quality);
            submitReview(quality);
        });
    });
}

function revealReviewAnswer() {
    const hiddenContent = document.getElementById('review-hidden-content');
    const qualityButtons = document.getElementById('quality-buttons');
    const revealBtn = document.getElementById('btn-reveal');

    if (hiddenContent) hiddenContent.style.display = 'block';
    if (qualityButtons) qualityButtons.style.display = 'block';
    if (revealBtn) revealBtn.style.display = 'none';

    isReviewRevealed = true;
}

async function submitReview(quality) {
    if (!currentReviewWord) return;

    try {
        const response = await fetch('/api/review/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: currentReviewWord.word_id,
                quality: quality
            })
        });

        if (!response.ok) throw new Error('Failed to submit review');

        const result = await response.json();
        showToast(`Rated ${quality}/5 ✓`, 'success');

        // Move to next word
        reviewIndex++;
        showNextReviewWord();

    } catch (error) {
        showToast('Failed to submit review', 'error');
        console.error(error);
    }
}

// ========================================
// ADD WORD
// ========================================

async function addWord() {
    const input = document.getElementById('word-input');
    const word = input?.value.trim();

    if (!word) {
        showToast('Please enter a word', 'error');
        return;
    }

    showLoading('Searching real news sources...');

    try {
        const response = await fetch('/api/words/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add word');
        }

        const result = await response.json();
        showToast(`Added: ${result.word}`, 'success');

        if (input) input.value = '';
        loadWords();

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ========================================
// WORD DETAIL MODAL
// ========================================

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
                <p><strong>Source:</strong> ${word.source_name || 'N/A'}</p>
                ${word.collocations ? `<p><strong>Collocations:</strong> ${word.collocations.join(', ')}</p>` : ''}
                ${word.synonyms ? `<p><strong>Synonyms:</strong> ${word.synonyms.join(', ')}</p>` : ''}
                ${word.antonyms ? `<p><strong>Antonyms:</strong> ${word.antonyms.join(', ')}</p>` : ''}
            </div>
            <div class="modal-footer">
                <button class="btn-primary btn-review-modal" data-word-id="${word.id}">🔄 Review</button>
                <button class="btn-secondary modal-close-btn">Close</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close handlers
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-close-btn').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    // Review button in modal - also uses the new endpoint
    modal.querySelector('.btn-review-modal').addEventListener('click', () => {
        modal.remove();
        startSingleWordReview(word.id);
    });
}

// ========================================
// DELETE WORD
// ========================================

async function deleteWord(wordId) {
    if (!confirm('Are you sure you want to delete this word?')) return;

    try {
        const response = await fetch(`/api/words/delete/${wordId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete');

        showToast('Word deleted', 'success');
        loadWords();

    } catch (error) {
        showToast('Failed to delete word', 'error');
    }
}

// ========================================
// QUIZ
// ========================================

async function loadQuizTab() {
    const container = document.getElementById('quiz-container');
    if (!container) return;

    try {
        const response = await fetch('/api/review/quiz');
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
                <div class="results-icon">🎯</div>
                <h2>Quiz Complete!</h2>
                <div class="score-display">${quizScore}/${quizQueue.length} (${percentage}%)</div>
                <p>${percentage >= 80 ? '🌟 Excellent!' : percentage >= 60 ? '👍 Good job!' : '💪 Keep practicing!'}</p>
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

    // Show feedback
    const options = document.querySelectorAll('.quiz-option');
    options.forEach((btn, i) => {
        btn.disabled = true;
        if (i === currentQuizQuestion.correct_index) {
            btn.classList.add('correct');
        } else if (i === selectedIndex && !isCorrect) {
            btn.classList.add('wrong');
        }
    });

    // Update review based on correctness
    try {
        await fetch('/api/review/quiz/answer', {
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

// ========================================
// STATS
// ========================================

async function loadStats() {
    try {
        const [overview, words, reviews] = await Promise.all([
            fetch('/api/stats/overview').then(r => r.json()),
            fetch('/api/stats/words').then(r => r.json()),
            fetch('/api/stats/reviews').then(r => r.json())
        ]);

        renderStats(overview, words, reviews);

    } catch (error) {
        showToast('Failed to load stats', 'error');
    }
}

function renderStats(overview, words, reviews) {
    const container = document.getElementById('stats-container');
    if (!container) return;

    const stats = overview.stats || {};

    container.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon blue">📚</div>
                <div class="stat-info">
                    <div class="stat-value">${words.total_words || 0}</div>
                    <div class="stat-label">Total Words</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">✅</div>
                <div class="stat-info">
                    <div class="stat-value">${words.learned_words || 0}</div>
                    <div class="stat-label">Learned</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon orange">🔄</div>
                <div class="stat-info">
                    <div class="stat-value">${reviews.due_words || 0}</div>
                    <div class="stat-label">Due Today</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon purple">🔥</div>
                <div class="stat-info">
                    <div class="stat-value">${stats.current_streak || 0}</div>
                    <div class="stat-label">Day Streak</div>
                </div>
            </div>
        </div>
        <div class="stats-mastery">
            <h3>🏆 Mastery Level</h3>
            <div class="mastery-badge">${stats.mastery_level || 'Novice'}</div>
        </div>
    `;
}

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Nav buttons
    Object.keys(navButtons).forEach(key => {
        if (navButtons[key]) {
            navButtons[key].addEventListener('click', () => switchTab(key));
        }
    });

    // Add word button
    const addBtn = document.getElementById('btn-add-word');
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

    // Load initial data
    loadWords();

    // Switch to default tab
    switchTab('words');
});