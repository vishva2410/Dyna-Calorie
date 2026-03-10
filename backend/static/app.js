// ================================================================
// DynaCalorie — Monochrome SPA
// Auth · Onboarding · Dashboard · Food Log · Weight Log
// ================================================================

const app = document.getElementById('app');

// ── State ─────────────────────────────────────────────────────────
let state = {
    token: localStorage.getItem('dc_token'),
    userId: localStorage.getItem('dc_user_id'),
    dashboard: null,
    history: null,
    meals: [],
};

function saveAuth(token, userId) {
    state.token = token;
    state.userId = userId;
    localStorage.setItem('dc_token', token);
    localStorage.setItem('dc_user_id', userId);
}

function clearAuth() {
    state = { token: null, userId: null, dashboard: null, history: null, meals: [] };
    localStorage.removeItem('dc_token');
    localStorage.removeItem('dc_user_id');
}

// ── API ───────────────────────────────────────────────────────────
function headers() {
    const h = { 'Content-Type': 'application/json' };
    if (state.token) h['Authorization'] = `Bearer ${state.token}`;
    return h;
}

async function api(method, path, body) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
}

const GET = (p) => api('GET', p);
const POST = (p, b) => api('POST', p, b);
const DEL = (p) => api('DELETE', p);

// ── Router ────────────────────────────────────────────────────────
async function go(page, p = {}) {
    app.innerHTML = '';
    window.scrollTo(0, 0);
    try {
        switch (page) {
            case 'auth': renderAuth(); break;
            case 'onboard': renderOnboarding(p.userId); break;
            case 'dashboard': await renderDashboard(); break;
            case 'log': await renderFoodLog(); break;
            case 'weight': renderWeightLog(); break;
            default: renderAuth();
        }
    } catch (e) {
        console.error(e);
        clearAuth();
        renderAuth();
    }
}

async function boot() {
    if (state.token && state.userId) {
        try { await loadDash(); go('dashboard'); } catch { clearAuth(); go('auth'); }
    } else go('auth');
}

async function loadDash() {
    state.dashboard = await GET(`/dashboard/${state.userId}`);
    try { state.history = await GET(`/dashboard/${state.userId}/history`); } catch { }
    try { state.meals = await GET(`/meals/${todayStr()}`); } catch { state.meals = []; }
}

function todayStr() { return new Date().toISOString().slice(0, 10); }

// ================================================================
// AUTH
// ================================================================
function renderAuth() {
    let isLogin = true;
    let loading = false;

    function draw() {
        app.innerHTML = `
            <div class="page" style="padding-top:80px;">
                <h1 style="margin-bottom:4px;">DYNACALORIE</h1>
                <p class="dim small" style="margin-bottom:32px;">Dynamic Calorie Management</p>
                <div class="tabs">
                    <button class="tab ${isLogin ? 'active' : ''}" id="t-login">Login</button>
                    <button class="tab ${!isLogin ? 'active' : ''}" id="t-reg">Register</button>
                </div>
                <div id="auth-err"></div>
                <div class="input-group">
                    <label>Email</label>
                    <input class="input" type="email" id="a-email" placeholder="you@example.com">
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input class="input" type="password" id="a-pass" placeholder="Min 8 characters">
                </div>
                <div class="mt-20">
                    <button class="btn btn-white" id="a-go" ${loading ? 'disabled' : ''}>
                        ${loading ? '<div class="spinner"></div>' : (isLogin ? 'Sign In' : 'Create Account')}
                    </button>
                </div>
            </div>`;
        $('t-login').onclick = () => { isLogin = true; draw(); };
        $('t-reg').onclick = () => { isLogin = false; draw(); };
        $('a-go').onclick = submit;
        $('a-pass').onkeydown = (e) => { if (e.key === 'Enter') submit(); };
    }

    async function submit() {
        const email = $('a-email').value.trim();
        const pass = $('a-pass').value.trim();
        if (!email.includes('@')) return err('auth-err', 'Enter a valid email.');
        if (pass.length < 8) return err('auth-err', 'Password must be at least 8 characters.');
        loading = true; draw();
        try {
            const d = await POST(isLogin ? '/auth/login' : '/auth/register', { email, password: pass });
            saveAuth(d.access_token, d.user_id);
            if (isLogin) { await loadDash(); go('dashboard'); }
            else go('onboard', { userId: d.user_id });
        } catch (e) { loading = false; draw(); err('auth-err', e.message); }
    }
    draw();
}

// ================================================================
// ONBOARDING
// ================================================================
function renderOnboarding(userId) {
    let step = 0, loading = false;
    const d = {
        age: '', gender: 'male', height: '', weight: '', bodyFat: '',
        neck: '', waist: '', hip: '', activity: 1.375, goal: 'fat_loss', rate: 0.5
    };

    const acts = [
        [1.2, 'Sedentary — desk job, no exercise'],
        [1.375, 'Light — 1–3 days/week'],
        [1.55, 'Moderate — 3–5 days/week'],
        [1.725, 'Active — 6–7 days/week'],
        [1.9, 'Athlete — 2× daily'],
    ];

    function draw() {
        const bars = [0, 1, 2].map(i => `<div class="step-bar ${i <= step ? 'done' : ''}"></div>`).join('');
        let content = '';

        if (step === 0) {
            content = `
                <h2>Basic Info</h2>
                <p class="dim small mb-16">Tell us about yourself</p>
                <div class="input-group"><label>Age</label><input class="input" type="number" id="o-age" value="${d.age}" placeholder="25"></div>
                <div class="input-group"><label>Gender</label>
                    <select class="input" id="o-gender">
                        <option value="male" ${d.gender === 'male' ? 'selected' : ''}>Male</option>
                        <option value="female" ${d.gender === 'female' ? 'selected' : ''}>Female</option>
                        <option value="other" ${d.gender === 'other' ? 'selected' : ''}>Other</option>
                    </select>
                </div>
                <div class="input-group"><label>Height (cm)</label><input class="input" type="number" id="o-height" value="${d.height}" placeholder="170"></div>`;
        } else if (step === 1) {
            content = `
                <h2>Body Composition</h2>
                <p class="dim small mb-16">For accurate metabolic rate calculation</p>
                <div class="input-group"><label>Weight (kg)</label><input class="input" type="number" step="0.1" id="o-weight" value="${d.weight}" placeholder="75"></div>
                <div class="input-group"><label>Body Fat % (optional)</label><input class="input" type="number" step="0.1" id="o-bf" value="${d.bodyFat}" placeholder="20"></div>
                <p class="dim small mt-16 mb-8">Or tape measurements:</p>
                <div class="row">
                    <div class="input-group"><label>Neck (cm)</label><input class="input" type="number" step="0.1" id="o-neck" value="${d.neck}" placeholder="38"></div>
                    <div class="input-group"><label>Waist (cm)</label><input class="input" type="number" step="0.1" id="o-waist" value="${d.waist}" placeholder="85"></div>
                </div>
                ${d.gender === 'female' ? '<div class="input-group"><label>Hips (cm)</label><input class="input" type="number" step="0.1" id="o-hip" value="' + d.hip + '" placeholder="95"></div>' : ''}
                <h3 class="mt-20 mb-8" style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--gray-400)">Activity Level</h3>
                ${acts.map(([v, l]) => `
                    <div class="radio-row ${d.activity === v ? 'sel' : ''}" data-v="${v}">
                        <div class="radio-circle"></div>
                        <span class="radio-text">${l}</span>
                    </div>`).join('')}`;
        } else {
            content = `
                <h2>Your Goal</h2>
                <p class="dim small mb-16">We'll compute your weekly calorie budget</p>
                <div class="goal-option ${d.goal === 'fat_loss' ? 'selected' : ''}" data-g="fat_loss">
                    <div class="goal-dot"></div><span class="goal-text">Fat Loss</span></div>
                <div class="goal-option ${d.goal === 'maintenance' ? 'selected' : ''}" data-g="maintenance">
                    <div class="goal-dot"></div><span class="goal-text">Maintenance</span></div>
                <div class="goal-option ${d.goal === 'muscle_gain' ? 'selected' : ''}" data-g="muscle_gain">
                    <div class="goal-dot"></div><span class="goal-text">Muscle Gain</span></div>
                <div class="mt-20">
                    <label class="dim small" style="display:block;margin-bottom:4px;">Target: <span class="mono" style="color:var(--white)">${d.rate.toFixed(2)}</span> kg/week</label>
                    <input type="range" min="0.1" max="1.5" step="0.05" value="${d.rate}" id="o-rate">
                </div>`;
        }

        app.innerHTML = `
            <div class="page" style="padding-top:24px;">
                <div class="steps">${bars}</div>
                <div id="ob-err"></div>
                ${content}
                <div class="mt-24 mb-20">
                    <button class="btn btn-white" id="o-next" ${loading ? 'disabled' : ''}>
                        ${loading ? '<div class="spinner"></div>' : (step < 2 ? 'Continue' : 'Start Tracking')}
                    </button>
                </div>
            </div>`;

        $('o-next').onclick = next;
        if (step === 1) document.querySelectorAll('.radio-row').forEach(el => el.onclick = () => { d.activity = parseFloat(el.dataset.v); draw(); });
        if (step === 2) {
            document.querySelectorAll('.goal-option').forEach(el => el.onclick = () => { d.goal = el.dataset.g; draw(); });
            const sl = $('o-rate'); if (sl) sl.oninput = () => { d.rate = parseFloat(sl.value); draw(); };
        }
    }

    function save() {
        const v = id => { const el = $(id); return el ? el.value : ''; };
        if (step === 0) { d.age = v('o-age'); d.gender = v('o-gender'); d.height = v('o-height'); }
        else if (step === 1) { d.weight = v('o-weight'); d.bodyFat = v('o-bf'); d.neck = v('o-neck'); d.waist = v('o-waist'); d.hip = v('o-hip'); }
    }

    async function next() {
        save();
        if (step === 0) {
            if (!parseInt(d.age) || parseInt(d.age) < 10) return err('ob-err', 'Enter valid age (10+).');
            if (!parseFloat(d.height) || parseFloat(d.height) < 100) return err('ob-err', 'Enter valid height.');
            step = 1; draw();
        } else if (step === 1) {
            if (!parseFloat(d.weight) || parseFloat(d.weight) < 30) return err('ob-err', 'Enter valid weight.');
            if (!parseFloat(d.bodyFat) && (!parseFloat(d.neck) || !parseFloat(d.waist))) return err('ob-err', 'Provide body fat % or neck + waist.');
            step = 2; draw();
        } else {
            loading = true; draw();
            try {
                const payload = {
                    user_id: userId, age: parseInt(d.age), gender: d.gender,
                    height_cm: parseFloat(d.height), weight_kg: parseFloat(d.weight),
                    activity_level: d.activity, goal: d.goal, target_rate: d.rate
                };
                if (parseFloat(d.bodyFat)) payload.body_fat = parseFloat(d.bodyFat);
                if (parseFloat(d.neck)) payload.neck_cm = parseFloat(d.neck);
                if (parseFloat(d.waist)) payload.waist_cm = parseFloat(d.waist);
                if (parseFloat(d.hip)) payload.hip_cm = parseFloat(d.hip);
                await POST('/auth/onboard', payload);
                await loadDash(); go('dashboard');
            } catch (e) { loading = false; draw(); err('ob-err', e.message); }
        }
    }
    draw();
}

// ================================================================
// DASHBOARD
// ================================================================
async function renderDashboard() {
    if (!state.dashboard) await loadDash();
    const d = state.dashboard;
    if (!d) { go('auth'); return; }

    const weekly = d.weekly_budget_kcal;
    const remaining = d.remaining_budget_kcal;
    const consumed = weekly - remaining;
    const pct = Math.min(Math.max(consumed / weekly, 0), 1);
    const calToday = d.calories_consumed_today;
    const proToday = d.protein_consumed_today;
    const proTarget = d.protein_target_g;
    const proPct = proTarget > 0 ? Math.min(proToday / proTarget, 1) : 0;
    const weight = d.current_weight_kg;
    const delta = d.expected_weight_change_kg;
    const warnings = d.guardrail_warnings || [];
    const dailyTarget = Math.round(weekly / 7);

    // Macros from today's meals
    let totP = 0, totC = 0, totF = 0;
    (state.meals || []).forEach(m => { totP += m.protein_g; totC += m.carbs_g; totF += m.fat_g; });
    const totMacro = totP + totC + totF || 1;

    // Ring chart SVG
    const R = 64, C = 2 * Math.PI * R;
    const ringOffset = C - (pct * C);

    const warningsHtml = warnings.map(w => `<div class="warning-bar">${esc(w)}</div>`).join('');

    // Meal list grouped
    const breakfast = (state.meals || []).filter(m => m.meal_type === 'breakfast');
    const lunch = (state.meals || []).filter(m => m.meal_type === 'lunch');
    const dinner = (state.meals || []).filter(m => m.meal_type === 'dinner');
    const snacks = (state.meals || []).filter(m => m.meal_type === 'snack');

    function mealGroupHtml(label, items) {
        if (items.length === 0) return '';
        const rows = items.map(m => `
            <div class="meal-entry">
                <div class="meal-info">
                    <div class="meal-name">${esc(m.food_name)}${m.servings !== 1 ? ` <span class="dim">×${m.servings}</span>` : ''}</div>
                    <div class="meal-macros">P ${m.protein_g.toFixed(0)}g · C ${m.carbs_g.toFixed(0)}g · F ${m.fat_g.toFixed(0)}g</div>
                </div>
                <span class="meal-cal">${Math.round(m.calories)}</span>
                <button class="meal-del" data-id="${m.id}" title="Remove">✕</button>
            </div>`).join('');
        return `<div class="meal-type-header">${label}</div>${rows}`;
    }

    let chartHtml = '';
    if (state.history) {
        const ch = state.history.calorie_history || [];
        if (ch.length > 0) {
            chartHtml = `<div class="card"><div class="card-header"><h3>Intake — Last 14 Days</h3></div><div class="chart-container"><canvas id="calChart"></canvas></div></div>`;
        }
    }

    app.innerHTML = `
        <div class="page">
            <div class="appbar">
                <h3 style="font-weight:700;color:var(--white);letter-spacing:-0.02em">DYNACALORIE</h3>
                <button class="btn-ghost" id="logout">Logout</button>
            </div>

            ${warningsHtml}

            <!-- Ring + Stats -->
            <div class="card" style="text-align:center;">
                <div class="ring-container" style="margin:8px auto 12px;">
                    <svg width="160" height="160" viewBox="0 0 160 160">
                        <circle cx="80" cy="80" r="${R}" fill="none" stroke="var(--gray-800)" stroke-width="8"/>
                        <circle cx="80" cy="80" r="${R}" fill="none" stroke="${pct > 1 ? 'var(--danger)' : 'var(--white)'}" stroke-width="8"
                            stroke-dasharray="${C}" stroke-dashoffset="${ringOffset}"
                            stroke-linecap="square" transform="rotate(-90 80 80)"
                            style="--circumference:${C}; animation: ringDraw 1s ease-out;"/>
                    </svg>
                    <div class="ring-label">
                        <span class="ring-value">${Math.round(remaining)}</span>
                        <span class="ring-unit">kcal left</span>
                    </div>
                </div>
                <p class="dim small">${Math.round(consumed)} of ${Math.round(weekly)} kcal this week</p>
            </div>

            <div class="stat-grid">
                <div class="stat-box"><div class="stat-label">Today</div><div class="stat-value">${Math.round(calToday)}</div></div>
                <div class="stat-box"><div class="stat-label">Daily Target</div><div class="stat-value">${dailyTarget}</div></div>
                <div class="stat-box"><div class="stat-label">Weight</div><div class="stat-value">${weight.toFixed(1)}</div></div>
                <div class="stat-box"><div class="stat-label">Δ Expected</div><div class="stat-value" style="color:${delta <= 0 ? '#4ADE4A' : '#FF3B3B'}">${delta > 0 ? '+' : ''}${delta.toFixed(2)}</div></div>
            </div>

            <!-- Protein -->
            <div class="card mt-8">
                <div class="card-header"><h3>Protein</h3><span class="mono small" style="color:${proPct >= 1 ? 'var(--success)' : 'var(--warning)'}">${proToday.toFixed(0)} / ${proTarget.toFixed(0)} g</span></div>
                <div class="bar-track"><div class="bar-fill ${proPct >= 1 ? 'success' : 'warning'}" style="width:${(proPct * 100).toFixed(0)}%"></div></div>
            </div>

            <!-- Macros -->
            <div class="card">
                <div class="card-header"><h3>Macros</h3></div>
                <div class="macro-legend">
                    <div class="macro-legend-item"><div class="macro-dot protein"></div>Protein ${totP.toFixed(0)}g</div>
                    <div class="macro-legend-item"><div class="macro-dot carbs"></div>Carbs ${totC.toFixed(0)}g</div>
                    <div class="macro-legend-item"><div class="macro-dot fat"></div>Fat ${totF.toFixed(0)}g</div>
                </div>
                <div class="macro-row">
                    <div class="macro-segment protein" style="width:${(totP / totMacro * 100).toFixed(0)}%">${totP > 0 ? Math.round(totP / totMacro * 100) + '%' : ''}</div>
                    <div class="macro-segment carbs" style="width:${(totC / totMacro * 100).toFixed(0)}%">${totC > 0 ? Math.round(totC / totMacro * 100) + '%' : ''}</div>
                    <div class="macro-segment fat" style="width:${(totF / totMacro * 100).toFixed(0)}%">${totF > 0 ? Math.round(totF / totMacro * 100) + '%' : ''}</div>
                </div>
            </div>

            <!-- Today's Meals -->
            <div class="card">
                <div class="card-header"><h3>Today's Meals</h3><span class="mono small dim">${(state.meals || []).length} items</span></div>
                ${(state.meals || []).length === 0 ? '<p class="dim small" style="padding:8px 0;">No food logged yet. Tap + to add.</p>' :
            mealGroupHtml('Breakfast', breakfast) +
            mealGroupHtml('Lunch', lunch) +
            mealGroupHtml('Dinner', dinner) +
            mealGroupHtml('Snack', snacks)}
            </div>

            ${chartHtml}

            <div class="row mt-8 mb-16">
                <button class="btn" id="btn-weight">⚖ Log Weight</button>
            </div>

            <div class="spacer"></div>
            <button class="fab" id="btn-log">+ Add Food</button>
        </div>`;

    $('logout').onclick = () => { clearAuth(); go('auth'); };
    $('btn-log').onclick = () => go('log');
    $('btn-weight').onclick = () => go('weight');
    document.querySelectorAll('.meal-del').forEach(el => {
        el.onclick = async () => {
            try { await DEL(`/meals/${el.dataset.id}`); await loadDash(); go('dashboard'); } catch { }
        };
    });

    // Chart
    if (state.history) buildCalChart(state.history.calorie_history || [], dailyTarget);
}

function buildCalChart(data, target) {
    const c = $('calChart');
    if (!c || data.length === 0) return;
    new Chart(c, {
        type: 'bar',
        data: {
            labels: data.map(d => d.date.slice(5)),
            datasets: [{
                data: data.map(d => d.calories_consumed),
                backgroundColor: data.map(d => d.calories_consumed > target ? '#FF3B3B' : '#FFFFFF'),
                borderWidth: 0, barPercentage: 0.6,
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: { duration: 800, easing: 'easeOutQuart' },
            plugins: {
                legend: { display: false },
                annotation: {
                    annotations: { target: { type: 'line', yMin: target, yMax: target, borderColor: '#5A5A5A', borderWidth: 1, borderDash: [4, 4] } }
                }
            },
            scales: {
                x: { display: true, grid: { display: false }, ticks: { color: '#5A5A5A', font: { size: 9 } } },
                y: { display: true, grid: { color: '#1A1A1A' }, ticks: { color: '#5A5A5A', font: { size: 9 } } },
            },
        },
    });
}

// ================================================================
// FOOD LOG
// ================================================================
async function renderFoodLog() {
    let query = '';
    let results = [];
    let mealType = 'snack';
    let cart = [];
    let customMode = false;
    let allFoods = [];
    let debounceTimer = null;

    try { allFoods = await GET('/foods'); } catch { }

    function draw() {
        const cartTotal = cart.reduce((s, c) => s + c.calories * c.servings, 0);
        const grouped = groupBy(query ? results : allFoods, 'category');

        let foodListHtml = '';
        for (const [cat, items] of Object.entries(grouped)) {
            foodListHtml += `<div class="food-category">${cat}</div>`;
            foodListHtml += items.map(f => `
                <div class="food-item" data-id="${f.id}" data-name="${esc(f.name)}" data-cal="${f.calories}" data-pro="${f.protein_g}" data-carb="${f.carbs_g}" data-fat="${f.fat_g}" data-serving="${esc(f.serving_size)}">
                    <div>
                        <div class="food-name">${esc(f.name)}</div>
                        <div class="food-meta">${f.serving_size} · P${f.protein_g}g C${f.carbs_g}g F${f.fat_g}g</div>
                    </div>
                    <span class="food-cal">${Math.round(f.calories)} cal</span>
                </div>`).join('');
        }

        const cartHtml = cart.length > 0 ? cart.map((c, i) => `
            <div class="meal-entry">
                <div class="meal-info">
                    <div class="meal-name">${esc(c.name)} <span class="dim">×${c.servings}</span></div>
                    <div class="meal-macros">${c.servingSize}</div>
                </div>
                <span class="meal-cal">${Math.round(c.calories * c.servings)}</span>
                <button class="meal-del" data-idx="${i}">✕</button>
            </div>`).join('') : '';

        app.innerHTML = `
            <div class="page">
                <div class="appbar">
                    <button class="back-btn" id="log-back">←</button>
                    <h3>Add Food</h3>
                    <button class="btn-ghost" id="custom-toggle">${customMode ? 'Search' : 'Custom'}</button>
                </div>

                <div class="tabs">
                    <button class="tab ${mealType === 'breakfast' ? 'active' : ''}" data-m="breakfast">Breakfast</button>
                    <button class="tab ${mealType === 'lunch' ? 'active' : ''}" data-m="lunch">Lunch</button>
                    <button class="tab ${mealType === 'dinner' ? 'active' : ''}" data-m="dinner">Dinner</button>
                    <button class="tab ${mealType === 'snack' ? 'active' : ''}" data-m="snack">Snack</button>
                </div>

                ${customMode ? `
                    <div id="log-err"></div>
                    <div class="input-group"><label>Food Name</label><input class="input" id="c-name" placeholder="e.g. Grilled Chicken"></div>
                    <div class="row">
                        <div class="input-group"><label>Calories</label><input class="input" type="number" id="c-cal" placeholder="0"></div>
                        <div class="input-group"><label>Protein (g)</label><input class="input" type="number" id="c-pro" placeholder="0"></div>
                    </div>
                    <div class="row">
                        <div class="input-group"><label>Carbs (g)</label><input class="input" type="number" id="c-carb" placeholder="0"></div>
                        <div class="input-group"><label>Fat (g)</label><input class="input" type="number" id="c-fat" placeholder="0"></div>
                    </div>
                    <button class="btn mt-8" id="c-add">Add to Meal</button>
                ` : `
                    <div class="search-wrap">
                        <span class="search-icon">⌕</span>
                        <input class="input" id="food-search" placeholder="Search foods..." value="${esc(query)}">
                    </div>
                    <div class="card" style="padding:0;max-height:300px;overflow-y:auto;">
                        ${foodListHtml || '<p class="dim small" style="padding:16px;">No results</p>'}
                    </div>
                `}

                ${cart.length > 0 ? `
                    <div class="card mt-12">
                        <div class="card-header"><h3>Cart</h3><span class="mono small" style="color:var(--white)">${Math.round(cartTotal)} cal</span></div>
                        ${cartHtml}
                    </div>
                    <button class="btn btn-white mt-8 mb-20" id="log-save">Log ${cart.length} Item${cart.length > 1 ? 's' : ''} — ${Math.round(cartTotal)} cal</button>
                ` : ''}
                <div class="spacer"></div>
            </div>`;

        // Events
        $('log-back').onclick = async () => { await loadDash(); go('dashboard'); };
        $('custom-toggle').onclick = () => { customMode = !customMode; draw(); };

        document.querySelectorAll('[data-m]').forEach(el => {
            el.onclick = () => { mealType = el.dataset.m; draw(); };
        });

        if (!customMode) {
            const searchInput = $('food-search');
            if (searchInput) {
                searchInput.oninput = () => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(async () => {
                        query = searchInput.value.trim();
                        if (query.length > 0) {
                            try { results = await GET(`/foods?q=${encodeURIComponent(query)}`); } catch { results = []; }
                        } else { results = []; }
                        draw();
                        const si = $('food-search');
                        if (si) { si.focus(); si.setSelectionRange(si.value.length, si.value.length); }
                    }, 250);
                };
            }

            document.querySelectorAll('.food-item').forEach(el => {
                el.onclick = () => {
                    cart.push({
                        name: el.dataset.name,
                        calories: parseFloat(el.dataset.cal),
                        protein: parseFloat(el.dataset.pro),
                        carbs: parseFloat(el.dataset.carb),
                        fat: parseFloat(el.dataset.fat),
                        servings: 1,
                        servingSize: el.dataset.serving,
                    });
                    draw();
                };
            });
        } else {
            const addBtn = $('c-add');
            if (addBtn) addBtn.onclick = () => {
                const name = $('c-name').value.trim();
                const cal = parseFloat($('c-cal').value) || 0;
                const pro = parseFloat($('c-pro').value) || 0;
                const carb = parseFloat($('c-carb').value) || 0;
                const fat = parseFloat($('c-fat').value) || 0;
                if (!name) return err('log-err', 'Enter food name.');
                if (cal <= 0) return err('log-err', 'Enter calories.');
                cart.push({ name, calories: cal, protein: pro, carbs: carb, fat: fat, servings: 1, servingSize: 'custom' });
                customMode = false; draw();
            };
        }

        document.querySelectorAll('.meal-del[data-idx]').forEach(el => {
            el.onclick = (e) => { e.stopPropagation(); cart.splice(parseInt(el.dataset.idx), 1); draw(); };
        });

        const saveBtn = $('log-save');
        if (saveBtn) saveBtn.onclick = saveAll;
    }

    async function saveAll() {
        for (const item of cart) {
            await POST('/meals', {
                date: todayStr(),
                meal_type: mealType,
                food_name: item.name,
                servings: item.servings,
                calories: item.calories * item.servings,
                protein_g: item.protein * item.servings,
                carbs_g: item.carbs * item.servings,
                fat_g: item.fat * item.servings,
            });
        }
        await loadDash();
        go('dashboard');
    }

    draw();
}

// ================================================================
// WEIGHT LOG
// ================================================================
function renderWeightLog() {
    let loading = false;

    function draw() {
        let chartHtml = '';
        if (state.history && state.history.weight_history && state.history.weight_history.length > 0) {
            chartHtml = `<div class="card mt-16"><div class="card-header"><h3>Weight Trend</h3></div><div class="chart-container"><canvas id="wChart"></canvas></div></div>`;
        }

        app.innerHTML = `
            <div class="page" style="padding-top:8px;">
                <div class="appbar">
                    <button class="back-btn" id="w-back">←</button>
                    <h3>Log Weight</h3>
                    <div style="width:32px"></div>
                </div>
                <div style="text-align:center;margin:24px 0 8px;">
                    <p class="dim small mb-8">Current weight</p>
                    <div class="big-num">${state.dashboard ? state.dashboard.current_weight_kg.toFixed(1) : '—'} kg</div>
                </div>
                <div id="w-err"></div>
                <div class="input-group mt-20">
                    <label>New Weight (kg)</label>
                    <input class="input input-big" type="number" step="0.1" id="w-val" placeholder="74.5">
                </div>
                <button class="btn btn-white mt-16" id="w-save" ${loading ? 'disabled' : ''}>
                    ${loading ? '<div class="spinner"></div>' : 'Save Weight'}
                </button>
                ${chartHtml}
            </div>`;

        $('w-back').onclick = () => go('dashboard');
        $('w-save').onclick = save;

        if (state.history && state.history.weight_history) buildWeightChart(state.history.weight_history);
    }

    async function save() {
        const w = parseFloat($('w-val').value);
        if (isNaN(w) || w <= 0) return err('w-err', 'Enter a valid weight.');
        loading = true; draw();
        try {
            await POST('/log/weight', { user_id: state.userId, weight_kg: w });
            await loadDash(); go('dashboard');
        } catch (e) { loading = false; draw(); err('w-err', e.message); }
    }

    draw();
}

function buildWeightChart(data) {
    const c = $('wChart');
    if (!c || !data || data.length === 0) return;
    new Chart(c, {
        type: 'line',
        data: {
            labels: data.map(d => d.date.slice(5)),
            datasets: [{
                data: data.map(d => d.weight_kg),
                borderColor: '#FFFFFF', backgroundColor: 'rgba(255,255,255,0.05)',
                fill: true, tension: 0.3, borderWidth: 2, pointRadius: 3,
                pointBackgroundColor: '#FFFFFF',
            }],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            animation: { duration: 800 },
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, grid: { display: false }, ticks: { color: '#5A5A5A', font: { size: 9 } } },
                y: { display: true, grid: { color: '#1A1A1A' }, ticks: { color: '#5A5A5A', font: { size: 9 } } },
            },
        },
    });
}

// ── Helpers ───────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function err(id, msg) { const el = $(id); if (el) el.innerHTML = `<div class="error-msg">${esc(msg)}</div>`; }
function groupBy(arr, key) {
    return arr.reduce((acc, item) => {
        const k = item[key] || 'other';
        (acc[k] = acc[k] || []).push(item);
        return acc;
    }, {});
}

// ── Boot ──────────────────────────────────────────────────────────
boot();
