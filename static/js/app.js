const byId = (id) => document.getElementById(id);
const fmt = (n) => (n ?? 0).toFixed ? n.toFixed(2) : n;

const state = {
  selected: {},
  allExercises: Array.isArray(window.__EXERCISES__) ? window.__EXERCISES__ : [],
};

function renderExerciseList(filter = '') {
  const list = byId('exercise-list');
  list.innerHTML = '';
  const q = filter.trim().toLowerCase();
  state.allExercises
    .filter((e) => e.toLowerCase().includes(q))
    .slice(0, 60)
    .forEach((name) => {
      const pill = document.createElement('button');
      pill.className = 'pill';
      pill.type = 'button';
      pill.textContent = name;
      pill.onclick = () => addSelected(name);
      list.appendChild(pill);
    });
}

function addSelected(name) {
  if (!state.selected[name]) state.selected[name] = { Reps: 20, Sets: 3 };
  renderSelected();
}

function removeSelected(name) {
  delete state.selected[name];
  renderSelected();
}

function renderSelected() {
  const grid = byId('selected-exercises');
  grid.innerHTML = '';
  Object.entries(state.selected).forEach(([name, vals]) => {
    const wrap = document.createElement('div');
    wrap.className = 'pill';
    const title = document.createElement('span');
    title.textContent = name;
    const repSet = document.createElement('div');
    repSet.className = 'rep-set';
    const reps = document.createElement('input');
    reps.type = 'number';
    reps.value = vals.Reps;
    reps.min = 1; reps.max = 100;
    reps.oninput = (e) => (state.selected[name].Reps = Number(e.target.value || 0));
    const sets = document.createElement('input');
    sets.type = 'number';
    sets.value = vals.Sets;
    sets.min = 1; sets.max = 10;
    sets.oninput = (e) => (state.selected[name].Sets = Number(e.target.value || 0));
    const del = document.createElement('button');
    del.type = 'button';
    del.textContent = '✕';
    del.onclick = () => removeSelected(name);
    repSet.append('Reps', reps, 'Sets', sets);
    wrap.append(title, repSet, del);
    grid.appendChild(wrap);
  });
}

let fatChart, repsChart;

async function predict() {
  const payload = {
    age: Number(byId('age').value),
    gender: byId('gender').value,
    weight: Number(byId('weight').value),
    height: Number(byId('height').value),
    session_duration: Number(byId('session_duration').value),
    frequency: Number(byId('frequency').value),
    exercises: state.selected,
  };

  const res = await fetch('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  renderResults(data);
  tryRenderCharts(data);
}

function renderResults(data) {
  const results = byId('results');
  results.classList.remove('hidden');
  if (data.error) {
    byId('recommendations').innerHTML = `<p class="warn">${data.error}</p>`;
    return;
  }
  byId('fat_pred').textContent = fmt(data.fat_pred);
  byId('ideal_fat').textContent = fmt(data.ideal_fat);
  byId('water_pred').textContent = fmt(data.water_pred);

  const rec = byId('recommendations');
  if ((data.total_rep_increase || 0) <= 0) {
    rec.innerHTML = '<p class="ok">✅ Your fat percentage is in the ideal range. Maintain your routine.</p>';
    return;
  }

  const items = Object.entries(data.rep_increase_each || {})
    .map(([ex, inc]) => `<li>🔹 ${ex}: +${inc} reps per session</li>`) 
    .join('');
  rec.innerHTML = `
    <h3>Recommendations</h3>
    <p class="warn">⚡ Increase your total workout volume by approx. <b>${data.total_rep_increase}</b> reps per session.</p>
    <ul>${items}</ul>
  `;
}

function tryRenderCharts(data){
  const fatEl = byId('fatChart');
  const repsEl = byId('repsChart');
  if (fatEl && window.Chart){
    const ds = {
      labels: ['Body Fat %'],
      datasets: [
        {label:'Current', data:[data.fat_pred || 0], backgroundColor:'rgba(124,92,255,0.75)'},
        {label:'Ideal', data:[data.ideal_fat || 0], backgroundColor:'rgba(0,212,255,0.75)'}
      ]
    };
    fatChart && fatChart.destroy();
    fatChart = new Chart(fatEl.getContext('2d'), {
      type:'bar',
      data: ds,
      options: {
        responsive:true,
        scales:{ y:{ beginAtZero:true, grid:{color:'rgba(255,255,255,0.08)'} }, x:{ grid:{display:false} } },
        plugins:{ legend:{ labels:{ color:'#e8ecff' } } }
      }
    });
  }

  if (repsEl && window.Chart){
    const names = Object.keys(state.selected || {});
    const current = names.map(n => (state.selected[n]?.Reps || 0));
    const incEach = data.rep_increase_each || {};
    const recommended = names.map(n => (state.selected[n]?.Reps || 0) + (incEach[n] || 0));
    repsChart && repsChart.destroy();
    repsChart = new Chart(repsEl.getContext('2d'), {
      type:'bar',
      data:{
        labels:names,
        datasets:[
          {label:'Current Reps', data:current, backgroundColor:'rgba(124,92,255,0.75)'},
          {label:'Recommended Reps', data:recommended, backgroundColor:'rgba(0,212,255,0.75)'}
        ]
      },
      options:{
        responsive:true,
        scales:{ y:{ beginAtZero:true, grid:{color:'rgba(255,255,255,0.08)'} }, x:{ ticks:{ color:'#e8ecff' }, grid:{display:false} } },
        plugins:{ legend:{ labels:{ color:'#e8ecff' } } }
      }
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  renderExerciseList('');
  renderSelected();
  byId('exercise-search').addEventListener('input', (e) => renderExerciseList(e.target.value));
  byId('predict').addEventListener('click', predict);
  // Try load profile if logged in
  fetch('/api/profile').then(r => r.json()).then(p => {
    if (!p || p.error) return;
    if (p.age) byId('age').value = p.age;
    if (p.gender) byId('gender').value = p.gender;
    if (p.weight) byId('weight').value = p.weight;
    if (p.height) byId('height').value = p.height;
    if (p.session_duration) byId('session_duration').value = p.session_duration;
    if (p.frequency) byId('frequency').value = p.frequency;
    try {
      const ex = JSON.parse(p.exercises_json || '{}');
      if (ex && typeof ex === 'object') {
        state.selected = ex;
        renderSelected();
      }
    } catch {}
  }).catch(() => {});

  const saveBtn = byId('saveProfile');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const payload = {
        age: Number(byId('age').value),
        gender: byId('gender').value,
        weight: Number(byId('weight').value),
        height: Number(byId('height').value),
        session_duration: Number(byId('session_duration').value),
        frequency: Number(byId('frequency').value),
        exercises_json: JSON.stringify(state.selected || {}),
      };
      const res = await fetch('/api/profile', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data && data.ok) {
        alert('Profile saved');
      } else {
        alert(data.error || 'Failed to save');
      }
    });
  }
});


