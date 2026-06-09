/**
 * AI Vocabulary Assistant - Frontend Logic
 * Handles: API calls, UI updates, review flow, quiz, stats
 */

// ========================================
// CONFIGURATION
// ========================================

const API_BASE = window.location.origin.includes('localhost') 
    ? 'http://localhost:8000' 
    : window.location.origin;

// ========================================
// STATE
// ========================================

let currentWords = [];
let reviewQueue = [];
let reviewIndex = 0;
let quizQueue = [];
let quizIndex = 0;
let quizScore = 0;

// ========================================
// DOM ELEMENTS
// ========================================

const elements = {
    wordInput: document.getElementById('word-input'),
    addBtn: document.getElementById('add-btn'),
    realExamplesToggle: document.getElementById('real-examples'),
    loading: document.getElementById('loading'),
    wordsGrid: document.getElementById('words-grid'),
    emptyWords: document.getElementById('empty-words'),
    reviewBadge: document.getElementById('review-badge'),
    streakCount: document.getElementById('streak-count'),
    wordCount: document.getElementById('word-count'),

    // Review elements
    reviewContainer: document.getElementById('review-container'),
    reviewCard: document.getElementById('review-card'),
    reviewWordText: document.getElementById('review-word-text'),
    reviewPhonetic: document.getElementById('review-phonetic'),
    reviewMeaning: document.getElementById('review-meaning'),
    reviewChinese: document.getElementById('review-chinese'),
    reviewExample: document.getElementById('review-example'),
    reviewTranslation: document.getElementById('review-translation'),
    revealBtn: document.getElementById('reveal-btn'),
    qualityButtons: document.getElementById('quality-buttons'),
    emptyReview: document.getElementById('empty-review'),
    startReviewBtn: document.getElementById('start-review-btn'),

    // Quiz elements
    quizContainer: document.getElementById('quiz-container'),
    quizCard: document.getElementById('quiz-card'),
    quizProgress: document.getElementById('quiz-progress'),
    quizCounter: document.getElementById('quiz-counter'),
    quizQuestionText: document.getElementById('quiz-question-text'),
    quizOptions: document.getElementById('quiz-options'),
    quizFeedback: document.getElementById('quiz-feedback'),
    feedbackIcon: document.getElementById('feedback-icon'),
    feedbackText: document.getElementById('feedback-text'),
    nextQuizBtn: document.getElementById('next-quiz-btn'),
    quizResults: document.getElementById('quiz-results'),
    quizScoreEl: document.getElementById('quiz-score'),
    quizTotalEl: document.getElementById('quiz-total'),
    quizMessage: document.getElementById('quiz-message'),
    retryQuizBtn: document.getElementById('retry-quiz-btn'),
    emptyQuiz: document.getElementById('empty-quiz'),
    startQuizBtn: document.getElementById('start-quiz-btn'),

    // Stats elements
    statTotal: document.getElementById('stat-total'),
    statLearned: document.getElementById('stat-learned'),
    statReviewed: document.getElementById('stat-reviewed'),
    statStreak: document.getElementById('stat-streak'),
    weeklyChart: document.getElementById('weekly-chart'),
    masteryText: document.getElementById('mastery-text'),

    // Toast
    toastContainer: document.getElementById('toast-container')
};

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initAddWord();
    initReview();
    initQuiz();
    initFilters();

    // Load initial data
    loadWords();
    loadStats();
    loadDueCount();
});

// ========================================
// NAVIGATION
// ========================================

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;

            // Update nav
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tab}`).classList.add('active');

            // Refresh data
            if (tab === 'stats') loadStats();
            if (tab === 'learn') loadWords();
        });
    });
}

// ========================================
// ADD WORD
// ========================================

function initAddWord() {
    elements.addBtn.addEventListener('click', handleAddWord);
    elements.wordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAddWord();
    });
}

async function handleAddWord() {
    const word = elements.wordInput.value.trim();
    if (!word) {
        showToast('Please enter a word', 'error');
        return;
    }

    const useRealExamples = elements.realExamplesToggle.checked;

    elements.loading.classList.remove('hidden');
    elements.addBtn.disabled = true;

    try {
        if (useRealExamples) {
            // Use Example Search Agent (Tavily + Qwen)
            const response = await fetch(`${API_BASE}/agents/example-search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ word })
            });

            const result = await response.json();

            if (result.success) {
                showToast(`Added "${word}" with real example!`, 'success');
                elements.wordInput.value = '';
                loadWords();
                loadStats();
                loadDueCount();
            } else {
                showToast(result.data?.error || 'Failed to add word', 'error');
            }
        } else {
            // Simple add without search
            const response = await fetch(`${API_BASE}/words/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ word })
            });

            const result = await response.json();
            showToast(`Added "${word}"!`, 'success');
            elements.wordInput.value = '';
            loadWords();
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        elements.loading.classList.add('hidden');
        elements.addBtn.disabled = false;
    }
}

// ========================================
// WORDS LIST
// ========================================

async function loadWords(filter = 'all') {
    try {
        const response = await fetch(`${API_BASE}/words/list?limit=100`);
        const words = await response.json();
        currentWords = words;

        renderWords(words, filter);
        elements.wordCount.textContent = words.length;
    } catch (error) {
        console.error('Failed to load words:', error);
    }
}

function renderWords(words, filter = 'all') {
    elements.wordsGrid.innerHTML = '';

    let filtered = words;
    if (filter === 'due') {
        // Filter due words (simplified - in production check review dates)
        filtered = words.filter(w => !w.learned);
    } else if (filter === 'learned') {
        filtered = words.filter(w => w.learned);
    }

    if (filtered.length === 0) {
        elements.emptyWords.classList.remove('hidden');
        return;
    }

    elements.emptyWords.classList.add('hidden');

    filtered.forEach(word => {
        const card = createWordCard(word);
        elements.wordsGrid.appendChild(card);
    });
}

function createWordCard(word) {
    const card = document.createElement('div');
    card.className = `word-card ${word.learned ? 'learned' : ''}`;

    const collocations = word.collocations ? word.collocations.slice(0, 2) : [];
    const tags = word.tags || [];

    card.innerHTML = `
        <div class="word-header">
            <div>
                <div class="word-title">${word.word}</div>
                <span class="word-phonetic">${word.phonetic || ''}</span>
            </div>
            <span class="word-pos">${word.part_of_speech || 'word'}</span>
        </div>
        <div class="word-meaning">${word.chinese_meaning || 'No meaning yet'}</div>
        ${word.example_sentence ? `
            <div class="word-example">"${word.example_sentence.substring(0, 120)}..."</div>
        ` : ''}
        ${word.source_name ? `
            <div class="word-source">
                <i class="fas fa-newspaper"></i>
                ${word.source_name}
                ${word.source_url ? `<a href="${word.source_url}" target="_blank"><i class="fas fa-external-link-alt"></i></a>` : ''}
            </div>
        ` : ''}
        ${collocations.length > 0 ? `
            <div class="word-tags">
                ${collocations.map(c => `<span class="tag">${c}</span>`).join('')}
            </div>
        ` : ''}
        <div class="word-actions">
            <button onclick="playAudio('${word.word}')">
                <i class="fas fa-volume-up"></i> Listen
            </button>
            <button onclick="startReviewWord(${word.id})">
                <i class="fas fa-sync-alt"></i> Review
            </button>
            <button onclick="deleteWord(${word.id})">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;

    card.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
            showWordDetail(word);
        }
    });

    return card;
}

function initFilters() {
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderWords(currentWords, btn.dataset.filter);
        });
    });
}

function showWordDetail(word) {
    // Create modal
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
                <p><strong>Part of Speech:</strong> ${word.part_of_speech || 'N/A'}</p>
                <p><strong>Meaning:</strong> ${word.chinese_meaning || 'N/A'}</p>
                <hr style="margin: 16px 0; border: none; border-top: 1px solid var(--border);">
                <p><strong>Example:</strong></p>
                <p style="font-style: italic; color: var(--text-secondary);">${word.example_sentence || 'N/A'}</p>
                <p style="color: var(--primary); margin-top: 8px;">${word.chinese_translation || ''}</p>
                <hr style="margin: 16px 0; border: none; border-top: 1px solid var(--border);">
                <p><strong>Source:</strong> ${word.source_name || 'N/A'}</p>
                ${word.source_url ? `<p><a href="${word.source_url}" target="_blank">Read Article <i class="fas fa-external-link-alt"></i></a></p>` : ''}
                ${word.collocations ? `<p><strong>Collocations:</strong> ${word.collocations.join(', ')}</p>` : ''}
                ${word.synonyms ? `<p><strong>Synonyms:</strong> ${word.synonyms.join(', ')}</p>` : ''}
                ${word.antonyms ? `<p><strong>Antonyms:</strong> ${word.antonyms.join(', ')}</p>` : ''}
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="playAudio('${word.word}')">
                    <i class="fas fa-volume-up"></i> Listen
                </button>
                <button class="btn-primary" onclick="startReviewWord(${word.id})">
                    <i class="fas fa-sync-alt"></i> Review Now
                </button>
            </div>
        </div>
    `;

    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    document.body.appendChild(modal);
}

async function deleteWord(wordId) {
    if (!confirm('Are you sure you want to delete this word?')) return;

    try {
        await fetch(`${API_BASE}/words/delete/${wordId}`, { method: 'DELETE' });
        showToast('Word deleted', 'success');
        loadWords();
        loadStats();
    } catch (error) {
        showToast('Failed to delete word', 'error');
    }
}

function playAudio(word) {
    // Placeholder for TTS - would integrate with Qwen TTS or browser TTS
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(word);
        utterance.lang = 'en-US';
        speechSynthesis.speak(utterance);
        showToast(`Playing: ${word}`, 'info');
    } else {
        showToast('Audio not supported in this browser', 'error');
    }
}

// ========================================
// REVIEW
// ========================================

function initReview() {
    elements.startReviewBtn.addEventListener('click', startReviewSession);
    elements.revealBtn.addEventListener('click', revealAnswer);

    // Quality buttons
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const quality = parseInt(btn.dataset.quality);
            submitReview(quality);
        });
    });
}

async function startReviewSession() {
    try {
        const response = await fetch(`${API_BASE}/review/due`);
        const result = await response.json();

        if (!result.success || result.due_count === 0) {
            elements.reviewCard.classList.add('hidden');
            elements.emptyReview.classList.remove('hidden');
            return;
        }

        reviewQueue = result.due_words;
        reviewIndex = 0;

        elements.emptyReview.classList.add('hidden');
        elements.reviewCard.classList.remove('hidden');

        showReviewCard();
    } catch (error) {
        showToast('Failed to load review words', 'error');
    }
}

function showReviewCard() {
    if (reviewIndex >= reviewQueue.length) {
        elements.reviewCard.classList.add('hidden');
        elements.emptyReview.classList.remove('hidden');
        elements.emptyReview.innerHTML = `
            <i class="fas fa-check-circle" style="color: var(--secondary);"></i>
            <p>Review complete! You reviewed ${reviewQueue.length} words.</p>
        `;
        loadDueCount();
        loadStats();
        return;
    }

    const word = reviewQueue[reviewIndex];

    elements.reviewWordText.textContent = word.word;
    elements.reviewPhonetic.textContent = word.phonetic || '';
    elements.reviewChinese.textContent = word.chinese_meaning || '';
    elements.reviewExample.textContent = word.example_sentence || '';
    elements.reviewTranslation.textContent = word.chinese_translation || '';

    // Reset state
    elements.reviewMeaning.classList.add('hidden');
    elements.revealBtn.classList.remove('hidden');
    elements.qualityButtons.classList.add('hidden');
}

function revealAnswer() {
    elements.reviewMeaning.classList.remove('hidden');
    elements.revealBtn.classList.add('hidden');
    elements.qualityButtons.classList.remove('hidden');
}

async function submitReview(quality) {
    const word = reviewQueue[reviewIndex];

    try {
        await fetch(`${API_BASE}/review/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_id: word.word_id, quality })
        });

        reviewIndex++;
        showReviewCard();
    } catch (error) {
        showToast('Failed to submit review', 'error');
    }
}

function startReviewWord(wordId) {
    // Switch to review tab and start with specific word
    document.querySelector('[data-tab="review"]').click();
    // In production, would filter review queue to start with this word
}

// ========================================
// QUIZ
// ========================================

function initQuiz() {
    elements.startQuizBtn.addEventListener('click', startQuizSession);
    elements.nextQuizBtn.addEventListener('click', showNextQuizQuestion);
    elements.retryQuizBtn.addEventListener('click', startQuizSession);
}

async function startQuizSession() {
    try {
        const response = await fetch(`${API_BASE}/review/quiz`);
        const result = await response.json();

        if (!result.success || !result.quiz || result.quiz.length === 0) {
            elements.quizCard.classList.add('hidden');
            elements.quizResults.classList.add('hidden');
            elements.emptyQuiz.classList.remove('hidden');
            return;
        }

        quizQueue = result.quiz;
        quizIndex = 0;
        quizScore = 0;

        elements.emptyQuiz.classList.add('hidden');
        elements.quizResults.classList.add('hidden');
        elements.quizCard.classList.remove('hidden');

        showNextQuizQuestion();
    } catch (error) {
        showToast('Failed to load quiz', 'error');
    }
}

function showNextQuizQuestion() {
    if (quizIndex >= quizQueue.length) {
        showQuizResults();
        return;
    }

    const question = quizQueue[quizIndex];

    // Update progress
    const progress = ((quizIndex + 1) / quizQueue.length) * 100;
    elements.quizProgress.style.width = `${progress}%`;
    elements.quizCounter.textContent = `${quizIndex + 1}/${quizQueue.length}`;

    // Update question
    elements.quizQuestionText.textContent = question.question;
    elements.quizFeedback.classList.add('hidden');

    // Update options
    elements.quizOptions.innerHTML = '';
    question.options.forEach((option, index) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option';
        btn.innerHTML = `
            <span class="option-letter">${String.fromCharCode(65 + index)}</span>
            <span>${option}</span>
        `;
        btn.addEventListener('click', () => handleQuizAnswer(index, question.correct_index, question.word_id));
        elements.quizOptions.appendChild(btn);
    });
}

async function handleQuizAnswer(selected, correct, wordId) {
    const isCorrect = selected === correct;

    if (isCorrect) {
        quizScore++;
    }

    // Show feedback
    const options = elements.quizOptions.querySelectorAll('.quiz-option');
    options[selected].classList.add(isCorrect ? 'correct' : 'wrong');
    if (!isCorrect) {
        options[correct].classList.add('correct');
    }

    // Disable all options
    options.forEach(opt => opt.style.pointerEvents = 'none');

    elements.feedbackIcon.textContent = isCorrect ? '🎉' : '😔';
    elements.feedbackText.textContent = isCorrect ? 'Correct! Great job!' : 'Not quite right. Keep practicing!';
    elements.quizFeedback.classList.remove('hidden');

    // Submit review based on correctness
    const quality = isCorrect ? 4 : 1;
    try {
        await fetch(`${API_BASE}/review/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_id: wordId, quality })
        });
    } catch (e) {
        console.error('Failed to submit quiz review:', e);
    }

    quizIndex++;
}

function showQuizResults() {
    elements.quizCard.classList.add('hidden');
    elements.quizResults.classList.remove('hidden');

    const percentage = Math.round((quizScore / quizQueue.length) * 100);

    elements.quizScoreEl.textContent = quizScore;
    elements.quizTotalEl.textContent = quizQueue.length;

    let message = '';
    if (percentage >= 80) {
        message = 'Excellent! You are mastering these words! 🌟';
    } else if (percentage >= 60) {
        message = 'Good job! Keep practicing! 👍';
    } else {
        message = 'Keep studying! You will get better! 💪';
    }
    elements.quizMessage.textContent = message;

    loadStats();
    loadDueCount();
}

// ========================================
// STATISTICS
// ========================================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats/overview`);
        const result = await response.json();

        if (result.success) {
            const stats = result.stats;
            elements.statTotal.textContent = stats.total_words;
            elements.statLearned.textContent = stats.learned_words;
            elements.statReviewed.textContent = stats.weekly_reviews;
            elements.statStreak.textContent = stats.current_streak;
            elements.streakCount.textContent = stats.current_streak;
            elements.masteryText.textContent = stats.mastery_level;

            // Update weekly chart (mock data for now)
            renderWeeklyChart();
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderWeeklyChart() {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const values = [3, 5, 2, 7, 4, 6, 8]; // Mock data
    const max = Math.max(...values);

    elements.weeklyChart.innerHTML = '';
    days.forEach((day, i) => {
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.style.height = `${(values[i] / max) * 100}%`;
        bar.setAttribute('data-day', day);
        elements.weeklyChart.appendChild(bar);
    });
}

async function loadDueCount() {
    try {
        const response = await fetch(`${API_BASE}/review/due`);
        const result = await response.json();

        if (result.success) {
            const count = result.due_count || 0;
            elements.reviewBadge.textContent = count;
            elements.reviewBadge.style.display = count > 0 ? 'block' : 'none';
        }
    } catch (error) {
        console.error('Failed to load due count:', error);
    }
}

// ========================================
// TOAST NOTIFICATIONS
// ========================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    toast.innerHTML = `<span>${icons[type]}</span> ${message}`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideUp 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
async function startQuizSession() {
    const response = await fetch(`${API_BASE}/review/quiz`);
    const result = await response.json();
    
    if (!result.success || !result.quiz || result.quiz.length === 0) {
        // Shows empty state
        return;
    }
    // Start quiz...
}