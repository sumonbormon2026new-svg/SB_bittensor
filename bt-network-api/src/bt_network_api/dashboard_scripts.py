"""JavaScript scripts for the dashboard, stored as a Python string literal."""

DASHBOARD_JS = r"""
async function api(path, opts) {
  opts = opts || {};
  var headers = { 'Content-Type': 'application/json' };
  if (apiToken) headers['Authorization'] = 'Bearer ' + apiToken;
  var r = await fetch(API + path, Object.assign({}, opts, {headers: headers}));
  if (r.status === 401) { alert('Unauthorized — set API key: setToken("your-key")'); return null; }
  if (!r.ok) {
    var txt = await r.text();
    var msg = 'HTTP ' + r.status;
    try { msg = JSON.parse(txt).detail || msg; } catch(e) {}
    throw new Error(msg);
  }
  return r.json();
}

function setToken(t) {
  apiToken = t;
  localStorage.setItem('bt_api_token', t);
  alert('Token set: ' + t.slice(0, 8) + '...');
}
window.setToken = setToken;

function loadToken() {
  apiToken = localStorage.getItem('bt_api_token') || '';
}
loadToken();

function getEl(id) { return document.getElementById(id); }

function fmtNum(n) {
  if (n == null) return '-';
  var f = parseFloat(n);
  if (isNaN(f)) return '-';
  if (f >= 1e9) return (f/1e9).toFixed(2)+'B';
  if (f >= 1e6) return (f/1e6).toFixed(2)+'M';
  if (f >= 1e3) return (f/1e3).toFixed(2)+'K';
  return f.toFixed(4);
}

function fmtAddr(s) {
  if (!s) return '-';
  return s.length > 16 ? s.slice(0,8)+'\u2026'+s.slice(-6) : s;
}

function fmtTs(ts) {
  if (!ts) return '-';
  return new Date(ts).toLocaleString();
}

function fmtMs(ms) {
  if (ms == null) return '-';
  return ms + 'ms';
}

function showError(el, msg) {
  el.textContent = msg;
  el.style.display = 'block';
}

function hideError(el) {
  el.style.display = 'none';
}

async function loadOverview() {
  try {
    var data = await Promise.all([api('/block'), api('/subnets'), api('/delegates')]);
    var block = data[0], subnets = data[1], delegates = data[2];
    getEl('kpi-block').textContent = fmtNum(block.block);
    getEl('kpi-block-time').textContent = block.cached ? 'cached @ ' + fmtTs(block.at) : 'live';
    getEl('kpi-subnets').textContent = subnets.count != null ? subnets.count : '-';
    getEl('kpi-delegates').textContent = delegates.count != null ? delegates.count : '-';
  } catch(e) { console.error(e); }
  loadCacheHistory();
}

async function loadCacheHistory() {
  try {
    var h = await api('/cache/history');
    var rows = h.records || [];
    if (!rows.length) {
      getEl('cache-history-table').innerHTML = '<div class="empty-state"><p>No cache history yet</p></div>';
      return;
    }
    var html = '<div class="data-table"><table><thead><tr><th>Time</th><th>Endpoint</th><th>Key</th><th>Status</th><th>Duration</th></tr></thead><tbody>';
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var sc = r.status_code;
      var scClass = sc >= 400 ? 'badge-red' : sc >= 300 ? 'badge-orange' : 'badge-green';
      html += '<tr><td class="muted">' + fmtTs(r.created_at) + '</td>' +
        '<td><code>' + r.endpoint + '</code></td>' +
        '<td class="mono faint" style="font-size:0.78rem">' + fmtAddr(r.key) + '</td>' +
        '<td><span class="badge ' + scClass + '">' + sc + '</span></td>' +
        '<td class="muted">' + fmtMs(r.duration_ms) + '</td></tr>';
    }
    html += '</tbody></table></div>';
    getEl('cache-history-table').innerHTML = html;
  } catch(e) {
    getEl('cache-history-table').innerHTML = '<div class="error-msg">Failed to load cache history</div>';
  }
}

async function lookupStake() {
  var addr = getEl('stake-address').value.trim();
  if (!addr) { showError(getEl('stake-error'), 'Please enter a coldkey address'); return; }
  hideError(getEl('stake-error'));
  getEl('stake-detail').style.display = 'none';
  getEl('stake-table-wrap').style.display = 'none';
  getEl('recent-stakes-msg').innerHTML = '<div class="loading">Loading stake data</div>';
  try {
    var data = await api('/staking/' + encodeURIComponent(addr));
    if (!data || !data.stakes) return;
    getEl('si-address').textContent = data.address;
    getEl('si-total').textContent = fmtNum(data.stakes.total_stake != null ? data.stakes.total_stake : 0);
    getEl('si-count').textContent = (data.stakes.stakes ? data.stakes.stakes.length : 0);
    getEl('si-cached').textContent = data.cached ? 'Yes @ ' + fmtTs(data.at) : 'No (fresh)';
    getEl('stake-detail').style.display = 'block';
    var stakes = data.stakes.stakes || [];
    if (!stakes.length) {
      getEl('stake-rows').innerHTML = '<tr><td colspan="6" class="muted" style="text-align:center;padding:20px">No stake records found</td></tr>';
    } else {
      var html = '';
      for (var i = 0; i < stakes.length; i++) {
        var s = stakes[i];
        html += '<tr><td class="mono" title="' + (s.hotkey_ss58 || '') + '">' + fmtAddr(s.hotkey_ss58) + '</td>' +
          '<td>' + (s.netuid != null ? s.netuid : '-') + '</td>' +
          '<td class="text-green">' + fmtNum(s.stake != null ? s.stake : 0) + '</td>' +
          '<td>' + fmtNum(s.hotkey_trust) + '</td>' +
          '<td>' + fmtNum(s.consensus) + '</td>' +
          '<td>' + fmtNum(s.hotkey_vtrust) + '</td></tr>';
      }
      getEl('stake-rows').innerHTML = html;
    }
    getEl('stake-table-wrap').style.display = 'block';
    getEl('recent-stakes-msg').innerHTML = '<div class="detail-panel"><h3>Stake for ' + fmtAddr(addr) + '</h3><p class="text-green">Total: ' + fmtNum(data.stakes.total_stake != null ? data.stakes.total_stake : 0) + ' TAO &bull; ' + stakes.length + ' stake entries</p></div>';
  } catch(e) {
    showError(getEl('stake-error'), 'Stake not found or network error: ' + e.message);
  }
}

function clearStake() {
  getEl('stake-address').value = '';
  getEl('stake-error').style.display = 'none';
  getEl('stake-detail').style.display = 'none';
  getEl('stake-table-wrap').style.display = 'none';
  getEl('recent-stakes-msg').innerHTML = '<div class="icon">&#128269;</div><p>Enter a coldkey address above to view stake details</p>';
}

async function loadSubnets() {
  var filterNetuid = getEl('subnet-netuid').value.trim();
  getEl('subnets-rows').innerHTML = '<tr><td colspan="8" class="loading">Loading subnets</td></tr>';
  try {
    var data = await api('/subnets');
    var subs = data.subnets || [];
    if (filterNetuid) {
      for (var i = subs.length-1; i >= 0; i--) {
        if (String(subs[i].netuid) !== filterNetuid) subs.splice(i, 1);
      }
    }
    if (!subs.length) {
      getEl('subnets-rows').innerHTML = '<tr><td colspan="8" class="muted" style="text-align:center;padding:20px">No subnets found</td></tr>';
      return;
    }
    var html = '';
    for (var i = 0; i < subs.length; i++) {
      var s = subs[i];
      html += '<tr><td><span class="badge badge-blue">' + (s.netuid != null ? s.netuid : '-') + '</span></td>' +
        '<td>' + (s.name || '-') + '</td>' +
        '<td>' + fmtNum(s.blocks_since_epoch != null ? s.blocks_since_epoch : 0) + '</td>' +
        '<td>' + fmtNum(s.max_n != null ? s.max_n : 0) + '</td>' +
        '<td class="text-green">' + fmtNum(s.min_stake != null ? s.min_stake : 0) + '</td>' +
        '<td class="text-purple">' + fmtNum(s.emission != null ? s.emission : 0) + '</td>' +
        '<td class="muted">' + fmtNum(s.difficulty != null ? s.difficulty : 0) + '</td>' +
        '<td class="muted">' + fmtTs(s.updated_at || s.created_at) + '</td></tr>';
    }
    getEl('subnets-rows').innerHTML = html;
  } catch(e) {
    getEl('subnets-rows').innerHTML = '<tr><td colspan="8" class="error-msg">' + e.message + '</td></tr>';
  }
}

async function loadDelegates() {
  var filter = (getEl('delegate-filter').value || '').toLowerCase();
  getEl('delegates-rows').innerHTML = '<tr><td colspan="8" class="loading">Loading delegates</td></tr>';
  try {
    var data = await api('/delegates');
    var dels = data.delegates || [];
    if (filter) {
      for (var i = dels.length-1; i >= 0; i--) {
        var d = dels[i];
        if (!((d.name||'').toLowerCase().includes(filter) || (d.delegate_ss58||'').toLowerCase().includes(filter))) {
          dels.splice(i, 1);
        }
      }
    }
    if (!dels.length) {
      getEl('delegates-rows').innerHTML = '<tr><td colspan="8" class="muted" style="text-align:center;padding:20px">No delegates found</td></tr>';
      return;
    }
    var html = '';
    for (var i = 0; i < dels.length; i++) {
      var d = dels[i];
      html += '<tr><td><strong>' + (d.name || '-') + '</strong></td>' +
        '<td class="mono" title="' + (d.delegate_ss58 || '') + '">' + fmtAddr(d.delegate_ss58) + '</td>' +
        '<td>' + fmtNum(d.nominators) + '</td>' +
        '<td class="text-green">' + fmtNum(d.apr) + '%</td>' +
        '<td class="text-purple">' + fmtNum(d.take) + '%</td>' +
        '<td>' + fmtNum(d.trust) + '</td>' +
        '<td class="muted">' + (d.image || '-') + '</td>' +
        '<td class="muted">' + (d.url || '-') + '</td></tr>';
    }
    getEl('delegates-rows').innerHTML = html;
  } catch(e) {
    getEl('delegates-rows').innerHTML = '<tr><td colspan="8" class="error-msg">' + e.message + '</td></tr>';
  }
}

async function loadAdmin() {
  try {
    var results = await Promise.all([api('/admin/stats'), api('/admin/keys')]);
    var stats = results[0], keys = results[1];
    getEl('admin-total-req').textContent = fmtNum(stats.total_requests);
    getEl('admin-avg-ms').textContent = fmtMs(stats.avg_response_ms);
    getEl('admin-active-keys').textContent = stats.active_api_keys;
    getEl('admin-total-keys').textContent = stats.total_api_keys;
    var klist = keys.keys || [];
    if (!klist.length) {
      getEl('admin-keys-rows').innerHTML = '<tr><td colspan="9" class="muted" style="text-align:center;padding:20px">No API keys</td></tr>';
      return;
    }
    var html = '';
    for (var i = 0; i < klist.length; i++) {
      var k = klist[i];
      var adminBadge = k.is_admin ? '<span class="badge badge-purple">Admin</span>' : '<span class="badge badge-blue">User</span>';
      var activeBadge = k.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-red">Revoked</span>';
      var revokeBtn = k.is_active && !k.is_admin ? '<button onclick="revokeKey(' + k.id + ')" class="btn-secondary" style="padding:4px 8px;font-size:0.75rem;border-radius:4px;cursor:pointer">Revoke</button>' : '';
      html += '<tr><td>' + k.id + '</td>' +
        '<td><strong>' + k.name + '</strong></td>' +
        '<td class="mono">' + k.key_prefix + '\u2026</td>' +
        '<td>' + adminBadge + '</td>' +
        '<td>' + activeBadge + '</td>' +
        '<td>' + k.query_count + '</td>' +
        '<td class="muted">' + fmtTs(k.created_at) + '</td>' +
        '<td class="muted">' + fmtTs(k.last_used_at) + '</td>' +
        '<td>' + revokeBtn + '</td></tr>';
    }
    getEl('admin-keys-rows').innerHTML = html;
  } catch(e) { console.error(e); }
}

async function createKey() {
  var name = getEl('new-key-name').value.trim() || 'default';
  try {
    var r = await api('/admin/keys?name=' + encodeURIComponent(name), {method: 'POST'});
    alert('API Key created!\nName: ' + r.name + '\nKey: ' + r.api_key + '\n\nSAVE THIS NOW - it cannot be retrieved later!');
    loadAdmin();
    getEl('new-key-name').value = '';
  } catch(e) { alert('Failed: ' + e.message); }
}

async function revokeKey(id) {
  if (!confirm('Revoke key #' + id + '?')) return;
  try {
    await api('/admin/keys/' + id + '/revoke', {method: 'POST'});
    loadAdmin();
  } catch(e) { alert('Failed: ' + e.message); }
}

// Tab switching
var tabs = document.querySelectorAll('.tab');
for (var i = 0; i < tabs.length; i++) {
  tabs[i].addEventListener('click', function() {
    for (var j = 0; j < tabs.length; j++) tabs[j].classList.remove('active');
    this.classList.add('active');
    var contents = document.querySelectorAll('.tab-content');
    for (var k = 0; k < contents.length; k++) contents[k].style.display = 'none';
    var tc = document.getElementById('tab-' + this.dataset.tab);
    if (tc) tc.style.display = 'block';
  });
}

// Navigation
var navLinks = document.querySelectorAll('.nav-link');
for (var i = 0; i < navLinks.length; i++) {
  navLinks[i].addEventListener('click', function(e) {
    e.preventDefault();
    for (var j = 0; j < navLinks.length; j++) navLinks[j].classList.remove('active');
    this.classList.add('active');
    var panels = document.querySelectorAll('.panel');
    for (var k = 0; k < panels.length; k++) panels[k].classList.remove('active');
    var panel = document.getElementById('panel-' + this.dataset.panel);
    if (panel) panel.classList.add('active');
    if (this.dataset.panel === 'subnets') loadSubnets();
    else if (this.dataset.panel === 'delegates') loadDelegates();
    else if (this.dataset.panel === 'admin') loadAdmin();
    else if (this.dataset.panel === 'overview') loadOverview();
  });
}

// Stake address enter key
getEl('stake-address').addEventListener('keydown', function(e) { if (e.key === 'Enter') lookupStake(); });

// Init
loadOverview();
"""
