async function loadState() {
  const fallback = await fetch('./sample-state.json').then((r) => r.json());
  return fallback;
}

function badgeClass(taxonomy) {
  return `badge ${taxonomy || 'observed'}`;
}

function metricCard(label, value) {
  return `<div class="kpi"><small>${label}</small><strong>${value}</strong></div>`;
}

function renderHero(state) {
  const chips = (state.project.focus || []).map((item) => `<span class="chip">${item}</span>`).join('');
  const metrics = state.metrics || {};
  document.getElementById('hero').innerHTML = `
    <div class="eyebrow">workflow interface · static ui · file-openable</div>
    <div class="hero-grid">
      <div>
        <h1>${state.project.name}</h1>
        <p class="lead">${state.project.tagline}. This interface presents the workflow as it exists today: branch-aware planning, evidence bundles, scientific checks, persisted evidence state, and resumable execution.</p>
        <div class="chips">${chips}</div>
      </div>
      <div class="panel">
        <h3>Current system profile</h3>
        <p class="muted">A browser-facing overview of the CLI workflow, aligned with the repository’s present terminology and outputs.</p>
        <div class="kpi-grid">
          ${metricCard('Rounds', metrics.roundsCompleted ?? '-')}
          ${metricCard('Branches', metrics.branchesThisRound ?? '-')}
          ${metricCard('Experiments', metrics.experimentsThisRound ?? '-')}
          ${metricCard('Claim taxonomy', metrics.claimTaxonomy ?? '-')}
        </div>
        <p class="footer-note">Resume ready: <strong>${metrics.resumeReady ? 'yes' : 'no'}</strong> · Evidence state: <strong>${metrics.evidenceState ? 'persisted' : 'not persisted'}</strong></p>
      </div>
    </div>
  `;
}

function renderWorkflow(state) {
  const cards = (state.workflow || []).map((item, index) => `
    <article class="step-card">
      <div class="step-badge accent-${item.accent}">${String(index + 1).padStart(2, '0')}</div>
      <h4>${item.step}</h4>
      <p><strong>${item.title}</strong></p>
      <p>${item.description}</p>
    </article>
  `).join('');
  document.getElementById('workflow-grid').innerHTML = cards;
}

function renderBranchTable(state) {
  const rows = (state.branchCards || []).map((card) => {
    const gaps = (card.gaps || []).map((gap) => `<span class="gap">${gap}</span>`).join('');
    const robustness = card.robustnessPassRate == null ? '-' : card.robustnessPassRate.toFixed(2);
    const constraints = card.constraintPassRate == null ? '-' : card.constraintPassRate.toFixed(2);
    return `
      <tr>
        <td><strong>${card.branchLabel}</strong></td>
        <td><span class="${badgeClass(card.taxonomy)}">${card.taxonomy}</span></td>
        <td>${card.mean.toFixed(4)}</td>
        <td>${card.std.toFixed(4)}</td>
        <td>${card.completedMembers}</td>
        <td>${card.incompleteMembers}</td>
        <td>${constraints}</td>
        <td>${robustness}</td>
        <td><div class="gaps">${gaps || '<span class="gap">none</span>'}</div></td>
      </tr>
    `;
  }).join('');

  document.getElementById('branch-table').innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Branch</th>
            <th>Taxonomy</th>
            <th>Mean</th>
            <th>Std</th>
            <th>Completed</th>
            <th>Incomplete</th>
            <th>Constraint pass</th>
            <th>Robustness pass</th>
            <th>Evidence gaps</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderPanels(state) {
  const makeList = (title, items) => `
    <div class="panel list-card">
      <h3>${title}</h3>
      <ul>${(items || []).map((item) => `<li>${item}</li>`).join('')}</ul>
    </div>
  `;
  document.getElementById('panel-grid').innerHTML = [
    makeList('Planning model', state.panels?.planning),
    makeList('Reliability model', state.panels?.reliability),
    makeList('Primary outputs', state.panels?.outputs)
  ].join('');
}

loadState().then((state) => {
  renderHero(state);
  renderWorkflow(state);
  renderBranchTable(state);
  renderPanels(state);
});
