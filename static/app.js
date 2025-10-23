let currentPage = 1
let perPage = 10

// Navigation helpers
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('d-none'))
  const el = document.getElementById(id)
  if (el) el.classList.remove('d-none')
}

document.getElementById('nav-home-link').onclick = e => { e.preventDefault(); showPage('page-home') }
document.getElementById('nav-upload-link').onclick = e => { e.preventDefault(); showPage('page-upload') }
document.getElementById('nav-dashboard-link').onclick = e => { e.preventDefault(); showPage('page-dashboard') }
document.getElementById('nav-records-link').onclick = e => { e.preventDefault(); showPage('page-records'); loadRecords(currentPage) }
document.getElementById('nav-about-link').onclick = e => { e.preventDefault(); showPage('page-about') }
document.getElementById('startUploadBtn').onclick = () => showPage('page-upload')

// Upload
document.getElementById('upload').onclick = async () => {
  const f = document.getElementById('file').files[0]
  const status = document.getElementById('uploadStatus')
  status.textContent = ''
  if (!f) return alert('select a CSV file')
  const fd = new FormData()
  fd.append('file', f)
  status.textContent = 'Uploading...'
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd })
    const j = await res.json()
    status.innerHTML = `<div class="alert alert-success p-1">Inserted: ${j.inserted || 0}</div>`
    if (j.errors && j.errors.length) {
      status.innerHTML += `<div class="alert alert-warning p-1">${j.errors.length} rows failed to import</div>`
    }
    loadRecords(1)
  } catch (e) {
    status.innerHTML = `<div class="alert alert-danger p-1">Upload failed: ${e.message}</div>`
  }
}

// Predict
document.getElementById('predict').onclick = async () => {
  const season = document.getElementById('season').value
  const res = await fetch('/api/prediction?season=' + encodeURIComponent(season))
  const j = await res.json()
  renderPredictionTable(j)
  if (j.prediction) {
    const labels = Object.keys(j.prediction)
    const data = labels.map(l => j.prediction[l].predicted_quantity)
    renderChart(labels, data)
  }
}

// Records pagination controls
document.getElementById('prevPage').onclick = () => { if (currentPage>1) loadRecords(currentPage-1) }
document.getElementById('nextPage').onclick = () => { loadRecords(currentPage+1) }
document.getElementById('perPageSelect').onchange = e => { perPage = parseInt(e.target.value); loadRecords(1) }

async function loadRecords(page=1) {
  const res = await fetch(`/api/records?page=${page}&per_page=${perPage}`)
  const rows = await res.json()
  const tbody = document.querySelector('#recordsTable tbody')
  tbody.innerHTML = ''
  rows.forEach(r => {
    const tr = document.createElement('tr')
    tr.innerHTML = `<td>${r.date}</td><td>${r.season}</td><td>${r.medicine}</td><td>${r.quantity}</td>`
    tbody.appendChild(tr)
  })
  currentPage = page
  document.getElementById('pageNum').textContent = String(currentPage)
}

function renderPredictionTable(j) {
  const tbody = document.querySelector('#predictionTable tbody')
  tbody.innerHTML = ''
  if (!j || !j.prediction) return
  Object.entries(j.prediction).forEach(([med, meta]) => {
    const tr = document.createElement('tr')
    const action = j.actions && j.actions[med] ? j.actions[med] : ''
    tr.innerHTML = `<td>${med}</td><td>${meta.predicted_quantity}</td><td>${meta.last_total}</td><td>${action}</td>`
    tbody.appendChild(tr)
  })
}

let chart = null
function renderChart(labels, data) {
  const ctx = document.getElementById('chart').getContext('2d')
  if (chart) chart.destroy()
  chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Predicted Quantity', data, backgroundColor: 'rgba(54,162,235,0.6)' }] },
    options: { responsive: true, maintainAspectRatio: false }
  })
}

// initial state
showPage('page-home')
loadRecords(1)
