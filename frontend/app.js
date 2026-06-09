// ========================================
// AI Vocabulary Assistant - Frontend
// Fully Fixed - Matches HTML Structure
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
let currentTab = 'learn';  // ← matches HTML data-tab="learn"
let currentFilter = 'all'; // 'all', 'due', 'learned'

// DOM Elements - MATCHING HTML IDs
const tabs = {
    learn: document.getElementById('tab-learn'),      // ← 'tab-learn'
    review: document.getElementById('tab-review'),
    quiz: document.getElementById('tab-quiz'),
    stats: document.getElementById('tab-stats')
};

// Nav buttons - select by data-tab
const navButtons = {
    learn: document.querySelector('[data-tab="learn"]'),
    review: document.querySelector('[data-tab="review"]'),
    quiz: document.querySelector('[data-tab="quiz"]'),
    stats: document.querySelector('[data-tab="stats"]')
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
    if (tabName === 'learn') loadWords();
    if (tabName === 'review') loadReviewTab();
    if (tabName === 'quiz') loadQuizTab();
    if (tabName === 'stats') loadStats();
}

// ========================================
// WORDS TAB (Learn Tab)
// ========================================

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

    // Filter words based on current filter
    let filteredWords = words;
    if (currentFilter === 'due') {
        filteredWords = words.filter(w => w.is_due);
    } else if (currentFilter === 'learned') {
        filteredWords = words.filter(w => w.learned);
    }

    if (filteredWords.length === 0) {
        container.innerHTML = '';
        if (emptyState) {
            emptyState.classList.remove('hidden');
            const emptyMsg = emptyState.querySelector('p');
            if (emptyMsg) {
                if (currentFilter === 'due') {
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

    attachWordCardListeners();
}

function attachWordCardListeners() {
    // Review button on word card
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


function setupFilterButtons() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Remove active from all filter buttons
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            // Add active to clicked button
            e.target.classList.add('active');
            // Update filter
            currentFilter = e.target.dataset.filter;
            // Re-render words
            renderWords();
        });
    });
}
// ========================================
// REVIEW
// ========================================

function resetReviewState() {
    reviewQueue = [];
    reviewIndex = 0;
    currentReviewWord = null;
    isReviewRevealed = false;
}

async function loadReviewTab() {
    const container = document.getElementById('review-container');
    const reviewCard = document.getElementById('review-card');
    const emptyReview = document.getElementById('empty-review');

    if (!container) return;

    try {
        const response = await fetch('/review/due');
        if (!response.ok) throw new Error('Failed to load due words');
        const data = await response.json();

        const dueWords = data.due_words || [];

        // Update badge
        const badge = document.getElementById('review-badge');
        if (badge) badge.textContent = dueWords.length;

        if (dueWords.length === 0) {
            if (reviewCard) reviewCard.classList.add('hidden');
            if (emptyReview) emptyReview.classList.remove('hidden');
            return;
        }

        if (emptyReview) emptyReview.classList.add('hidden');

        // Show start review button with due count
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

function startReviewSession(dueWords) {
    resetReviewState();
    reviewQueue = [...dueWords];
    reviewIndex = 0;
    showNextReviewWord();
}

async function startSingleWordReview(wordId) {
    resetReviewState();
    switchTab('review');

    const container = document.getElementById('review-container');
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
            chinese_translation: data.chinese_translation
        }];
        reviewIndex = 0;

        hideLoading();
        showNextReviewWord();

    } catch (error) {
        hideLoading();
        showToast(error.message, 'error');
        container.innerHTML = `
            <div class="empty-state">
                <p>❌ ${error.message}</p>
                <button class="btn-primary" onclick="switchTab('learn')">Back to Words</button>
            </div>
        `;
    }
}

function showNextReviewWord() {
    const container = document.getElementById('review-container');
    const reviewCard = document.getElementById('review-card');
    const emptyReview = document.getElementById('empty-review');

    if (!container) return;

    if (reviewIndex >= reviewQueue.length) {
        container.innerHTML = `
            <div class="review-complete">
                <h2>🎉 Review Complete!</h2>
                <p>You reviewed ${reviewQueue.length} words.</p>
                <button id="btn-review-again" class="btn-primary">Review Again</button>
                <button id="btn-back-menu" class="btn-secondary">Back to Words</button>
            </div>
        `;

        document.getElementById('btn-review-again')?.addEventListener('click', () => {
            resetReviewState();
            loadReviewTab();
        });

        document.getElementById('btn-back-menu')?.addEventListener('click', () => {
            switchTab('learn');
        });

        return;
    }

    currentReviewWord = reviewQueue[reviewIndex];
    isReviewRevealed = false;

    // Use the existing HTML structure
    if (reviewCard) {
        reviewCard.classList.remove('hidden');
        if (emptyReview) emptyReview.classList.add('hidden');

        document.getElementById('review-word-text').textContent = currentReviewWord.word;
        document.getElementById('review-phonetic').textContent = currentReviewWord.phonetic || '';
        document.getElementById('review-chinese').textContent = currentReviewWord.chinese_meaning || 'N/A';
        document.getElementById('review-example').textContent = currentReviewWord.example_sentence || '';
        document.getElementById('review-translation').textContent = currentReviewWord.chinese_translation || '';

        // Reset reveal state
        document.getElementById('review-meaning').classList.add('hidden');
        document.getElementById('reveal-btn').classList.remove('hidden');
        document.getElementById('quality-buttons').classList.add('hidden');
    } else {
        // Fallback if HTML structure is different
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

        document.getElementById('btn-reveal')?.addEventListener('click', revealReviewAnswer);
        document.querySelectorAll('.quality-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const quality = parseInt(e.target.dataset.quality);
                submitReview(quality);
            });
        });
    }
}

function revealReviewAnswer() {
    const meaning = document.getElementById('review-meaning');
    const revealBtn = document.getElementById('reveal-btn');
    const qualityButtons = document.getElementById('quality-buttons');

    if (meaning) meaning.classList.remove('hidden');
    if (revealBtn) revealBtn.classList.add('hidden');
    if (qualityButtons) qualityButtons.classList.remove('hidden');

    isReviewRevealed = true;
}

async function submitReview(quality) {
    if (!currentReviewWord) return;

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

        showToast(`Rated ${quality}/5 ✓`, 'success');
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

// ========================================
// DELETE WORD
// ========================================

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

// ========================================
// QUIZ
// ========================================

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

// ========================================
// STATS
// ========================================

async function loadStats() {
    try {
        const [overview, words, reviews] = await Promise.all([
            fetch('/stats/overview').then(r => r.json()),
            fetch('/stats/words').then(r => r.json()),
            fetch('/stats/reviews').then(r => r.json())
        ]);

        renderStats(overview, words, reviews);

    } catch (error) {
        showToast('Failed to load stats', 'error');
    }
}

function renderStats(overview, words, reviews) {
    const stats = overview.stats || {};

    document.getElementById('stat-total').textContent = words.total_words || 0;
    document.getElementById('stat-learned').textContent = words.learned_words || 0;
    document.getElementById('stat-reviewed').textContent = reviews.weekly_reviews || 0;
    document.getElementById('stat-streak').textContent = stats.current_streak || 0;
    document.getElementById('mastery-text').textContent = stats.mastery_level || 'Novice';
}

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Nav buttons - use data-tab from HTML
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            if (tabName) switchTab(tabName);
        });
    });

    // Add word button - matches HTML id="add-btn"
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

    // Review tab start button
    const startReviewBtn = document.getElementById('start-review-btn');
    if (startReviewBtn) {
        startReviewBtn.addEventListener('click', () => loadReviewTab());
    }

    // Quiz tab start button
    const startQuizBtn = document.getElementById('start-quiz-btn');
    if (startQuizBtn) {
        startQuizBtn.addEventListener('click', () => loadQuizTab());
    }

    // Reveal button in review card
    const revealBtn = document.getElementById('reveal-btn');
    if (revealBtn) {
        revealBtn.addEventListener('click', revealReviewAnswer);
    }

    // Quality buttons in review card
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const quality = parseInt(e.target.dataset.quality);
            submitReview(quality);
        });
    });

        // Add filter button handlers
    const filterAll = document.getElementById('filter-all');
    const filterDue = document.getElementById('filter-due');
    const filterLearned = document.getElementById('filter-learned');
    
    [filterAll, filterDue, filterLearned].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', (e) => {
                // Remove active from all
                [filterAll, filterDue, filterLearned].forEach(b => b?.classList.remove('active'));
                // Add active to clicked
                e.target.classList.add('active');
                // Update filter
                currentFilter = e.target.id.replace('filter-', '');
                // Re-render
                renderWords();
            });
        }
    });

    setupFilterButtons();

    // Load initial data
    loadWords();

    // Switch to default tab
    switchTab('learn');
});