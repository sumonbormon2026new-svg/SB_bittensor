"""Dashboard page with full Stake, Subnets, and Network views."""

from functools import lru_cache

from fastapi import Request
from fastapi.responses import HTMLResponse

from bt_network_api.dashboard_scripts import DASHBOARD_JS


@lru_cache(maxsize=1)
def _js_source() -> str:
    return DASHBOARD_JS


def _build_js() -> str:
    return _js_source()


def get_api_base(req: Request) -> str:
    scheme = req.headers.get("x-forwarded-proto", req.url.scheme)
    host = req.headers.get("x-forwarded-host", str(req.url.netloc))
    return f"{scheme}://{host}"


def render_dashboard(req: Request, network: str, version: str, auth_required: bool) -> HTMLResponse:
    api_base = get_api_base(req)
    js = _build_js()

    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stake Dashboard — bt-network-api</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
:root {{ --bg: #0d1117; --surface: #161b22; --surface2: #21262d; --border: #30363d; --text: #c9d1d9; --muted: #8b949e; --green: #3fb950; --red: #f85149; --blue: #58a6ff; --purple: #bc8cff; --orange: #e3b341; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; min-height: 100vh; }}
.sidebar {{ width: 220px; background: var(--surface); border-right: 1px solid var(--border); padding: 24px 16px; display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; position: fixed; top: 0; left: 0; height: 100vh; overflow-y: auto; }}
.sidebar .logo {{ font-size: 1.1rem; font-weight: 700; color: var(--green); padding: 8px 12px 20px; letter-spacing: -0.02em; }}
.sidebar .logo span {{ color: var(--muted); font-weight: 400; font-size: 0.8rem; }}
.sidebar a {{ display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 6px; color: var(--muted); text-decoration: none; font-size: 0.88rem; transition: background 0.15s, color 0.15s; }}
.sidebar a:hover {{ background: var(--surface2); color: var(--text); }}
.sidebar a.active {{ background: rgba(56,139,253,0.15); color: var(--blue); }}
.sidebar a svg {{ width: 16px; height: 16px; opacity: 0.8; flex-shrink: 0; }}
.sidebar .section-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); padding: 16px 12px 6px; }}
.sidebar .status-bar {{ margin-top: auto; padding: 12px; font-size: 0.75rem; color: var(--muted); border-top: 1px solid var(--border); }}
.main {{ flex: 1; margin-left: 220px; padding: 28px 32px; max-width: 1400px; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
h2 {{ font-size: 1.4rem; font-weight: 600; margin-bottom: 6px; }}
.subtitle {{ color: var(--muted); font-size: 0.88rem; margin-bottom: 24px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
.kpi {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; transition: border-color 0.2s; }}
.kpi:hover {{ border-color: var(--blue); }}
.kpi .label {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }}
.kpi .value {{ font-size: 1.7rem; font-weight: 700; line-height: 1; }}
.kpi .value.green {{ color: var(--green); }}
.kpi .value.blue {{ color: var(--blue); }}
.kpi .value.purple {{ color: var(--purple); }}
.kpi .value.orange {{ color: var(--orange); }}
.kpi .sub {{ font-size: 0.78rem; color: var(--muted); margin-top: 6px; }}
.search-wrap {{ display: flex; gap: 10px; margin-bottom: 24px; }}
.search-wrap input {{ flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; color: var(--text); font-size: 0.92rem; outline: none; transition: border-color 0.2s; }}
.search-wrap input:focus {{ border-color: var(--blue); }}
.search-wrap input::placeholder {{ color: var(--muted); }}
.search-wrap button {{ background: var(--blue); color: #fff; border: none; border-radius: 8px; padding: 10px 20px; font-size: 0.88rem; cursor: pointer; transition: opacity 0.15s; }}
.search-wrap button:hover {{ opacity: 0.85; }}
.search-wrap .btn-secondary {{ background: var(--surface2); color: var(--text); border: 1px solid var(--border); }}
.search-wrap .btn-secondary:hover {{ border-color: var(--blue); color: var(--blue); }}
.data-table {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
.data-table table {{ width: 100%; border-collapse: collapse; }}
.data-table thead tr {{ border-bottom: 1px solid var(--border); }}
.data-table th {{ text-align: left; padding: 12px 16px; font-size: 0.75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.data-table td {{ padding: 11px 16px; font-size: 0.88rem; border-bottom: 1px solid var(--border); vertical-align: middle; }}
.data-table tr:last-child td {{ border-bottom: none; }}
.data-table tr:hover td {{ background: var(--surface2); }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.75rem; font-weight: 500; }}
.badge-green {{ background: rgba(63,185,80,0.15); color: var(--green); }}
.badge-red {{ background: rgba(248,81,73,0.15); color: var(--red); }}
.badge-blue {{ background: rgba(88,166,255,0.15); color: var(--blue); }}
.badge-purple {{ background: rgba(188,140,255,0.15); color: var(--purple); }}
.badge-orange {{ background: rgba(227,179,65,0.15); color: var(--orange); }}
.mono {{ font-family: 'SF Mono','Fira Code','Cascadia Code',monospace; font-size: 0.85rem; }}
.muted {{ color: var(--muted); }}
.faint {{ color: #4d5566; }}
.text-green {{ color: var(--green); }}
.text-red {{ color: var(--red); }}
.text-blue {{ color: var(--blue); }}
.address {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }}
.loading {{ text-align: center; padding: 40px; color: var(--muted); font-size: 0.9rem; }}
.loading::after {{ content: '...'; animation: dots 1.2s steps(4,end) infinite; }}
@keyframes dots {{ 0%,20% {{ content: '.'; }} 40% {{ content: '..'; }} 60%,100% {{ content: '...'; }} }}
.error-msg {{ background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3); border-radius: 8px; padding: 16px; color: var(--red); margin-bottom: 20px; }}
.empty-state {{ text-align: center; padding: 60px 20px; color: var(--muted); }}
.empty-state .icon {{ font-size: 3rem; margin-bottom: 16px; opacity: 0.3; }}
.tabs {{ display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }}
.tab {{ padding: 8px 16px; cursor: pointer; font-size: 0.88rem; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color 0.15s, border-color 0.15s; }}
.tab:hover {{ color: var(--text); }}
.tab.active {{ color: var(--blue); border-bottom-color: var(--blue); }}
.detail-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
.detail-panel h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 12px; color: var(--text); }}
.detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
.detail-item .di-label {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 3px; }}
.detail-item .di-value {{ font-size: 0.92rem; font-weight: 500; }}
.chart-bar {{ background: var(--surface2); border-radius: 4px; height: 6px; margin-top: 6px; overflow: hidden; }}
.chart-bar-fill {{ height: 100%; background: var(--blue); border-radius: 4px; transition: width 0.5s ease; }}
@media (max-width: 768px) {{ .sidebar {{ width: 60px; padding: 16px 8px; }} .sidebar .logo span, .sidebar a span, .sidebar .section-label, .sidebar .status-bar span {{ display: none; }} .sidebar a {{ justify-content: center; padding: 10px; }} .main {{ margin-left: 60px; padding: 16px; }} }}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="logo">bt-network-api <span>v{version}</span></div>
  <a href="#" class="nav-link active" data-panel="overview">
    <svg viewBox="0 0 16 16" fill="currentColor"><path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z"/></svg>
    <span>Overview</span>
  </a>
  <a href="#" class="nav-link" data-panel="stake">
    <svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a.5.5 0 0 1 .5.5v5h4a.5.5 0 0 1 0 1h-4v4a.5.5 0 0 1-1 0v-4H3.5a.5.5 0 0 1 0-1H7V1.5A.5.5 0 0 1 7.5 1z"/></svg>
    <span>Stake Lookup</span>
  </a>
  <a href="#" class="nav-link" data-panel="subnets">
    <svg viewBox="0 0 16 16" fill="currentColor"><path d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5 0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8a.5.5 0 0 1 .5-.5h1A1.5 1.5 0 0 1 10 4.5v1A1.5 1.5 0 0 1 8.5 7H7v1A1.5 1.5 0 0 1 5.5 9.5v1A1.5 1.5 0 0 1 4 9.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 3 9h-.5v.5A.5.5 0 0 1 2 10v.5a.5.5 0 0 1-1 0v-.5A1.5 1.5 0 0 1 .5 9.5v-1A1.5 1.5 0 0 1 2 7h1v-1A1.5 1.5 0 0 1 4.5 4.5v-1A1.5 1.5 0 0 1 6 1.5v1A.5.5 0 0 1 6 2H5a.5.5 0 0 1 0-1h3zm0 1h4a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5z"/></svg>
    <span>Subnets</span>
  </a>
  <a href="#" class="nav-link" data-panel="delegates">
    <svg viewBox="0 0 16 16" fill="currentColor"><path d="M3.5 2A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-9A1.5 1.5 0 0 0 12.5 2h-9zm-.5 13a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5v-1zm.5-2.5a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5zm0-2a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5zm.5 4.5a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1h-3zM2 10a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm2.5 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/></svg>
    <span>Delegates</span>
  </a>
  <a href="#" class="nav-link" data-panel="admin">
    <svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 2a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm2.5 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2 10a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm2.5 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm4.5 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM10 8a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm2.5 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm0-6.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 1 0v-1a.5.5 0 0 0-.5-.5z"/></svg>
    <span>Admin</span>
  </a>
  <div class="status-bar">
    <span>Network: <strong>{network}</strong></span><br>
    <span>Auth: <strong>{"Yes" if auth_required else "No"}</strong></span>
  </div>
</nav>
<main class="main">
  <div id="panel-overview" class="panel active">
    <h2>Network Overview</h2>
    <p class="subtitle">Real-time Bittensor network statistics on <strong>{network}</strong></p>
    <div class="kpi-grid">
      <div class="kpi"><div class="label">Current Block</div><div class="value blue" id="kpi-block">—</div><div class="sub" id="kpi-block-time"></div></div>
      <div class="kpi"><div class="label">Active Subnets</div><div class="value green" id="kpi-subnets">—</div><div class="sub">registered subnets</div></div>
      <div class="kpi"><div class="label">Delegates</div><div class="value purple" id="kpi-delegates">—</div><div class="sub">registered delegates</div></div>
      <div class="kpi"><div class="label">Total Stake (TAO)</div><div class="value orange" id="kpi-total-stake">—</div><div class="sub">across all coldkeys</div></div>
    </div>
    <div class="detail-panel">
      <h3>Network Status</h3>
      <div class="detail-grid">
        <div class="detail-item"><div class="di-label">Network</div><div class="di-value text-blue">{network}</div></div>
        <div class="detail-item"><div class="di-label">Version</div><div class="di-value">{version}</div></div>
        <div class="detail-item"><div class="di-label">Auth Required</div><div class="di-value">{"Yes" if auth_required else "No"}</div></div>
        <div class="detail-item"><div class="di-label">API Base</div><div class="di-value mono" style="font-size:0.75rem">{api_base}</div></div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab active" data-tab="recent-stakes">Recent Stakes</div>
      <div class="tab" data-tab="cache-history">Cache History</div>
    </div>
    <div id="tab-recent-stakes" class="tab-content">
      <div id="recent-stakes-msg" class="empty-state"><div class="icon">🔍</div><p>Enter a coldkey address above to view stake details</p></div>
    </div>
    <div id="tab-cache-history" class="tab-content" style="display:none">
      <div id="cache-history-table"></div>
    </div>
  </div>

  <div id="panel-stake" class="panel">
    <h2>Stake Lookup</h2>
    <p class="subtitle">Search staking information by coldkey address</p>
    <div class="search-wrap">
      <input type="text" id="stake-address" placeholder="Enter coldkey address (e.g., 5FfX...)" />
      <button onclick="lookupStake()">Search</button>
      <button class="btn-secondary" onclick="clearStake()">Clear</button>
    </div>
    <div id="stake-error" class="error-msg" style="display:none"></div>
    <div id="stake-detail" style="display:none">
      <div class="detail-panel" style="margin-bottom:16px">
        <h3>Stake Info</h3>
        <div class="detail-grid">
          <div class="detail-item"><div class="di-label">Coldkey</div><div class="di-value mono" id="si-address">—</div></div>
          <div class="detail-item"><div class="di-label">Total Stake</div><div class="di-value text-green" id="si-total">—</div></div>
          <div class="detail-item"><div class="di-label">Stake Count</div><div class="di-value" id="si-count">—</div></div>
          <div class="detail-item"><div class="di-label">Cached</div><div class="di-value" id="si-cached">—</div></div>
        </div>
      </div>
    </div>
    <div id="stake-table-wrap" style="display:none">
      <div class="data-table">
        <table>
          <thead><tr><th>Hotkey</th><th>Netuid</th><th>Stake (TAO)</th><th>Trust</th><th>Consensus</th><th>VTrust</th></tr></thead>
          <tbody id="stake-rows"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div id="panel-subnets" class="panel">
    <h2>Subnets</h2>
    <p class="subtitle">All registered subnets on the Bittensor network</p>
    <div class="search-wrap">
      <input type="number" id="subnet-netuid" placeholder="Filter by netuid" min="0" />
      <button onclick="loadSubnets()">Refresh</button>
    </div>
    <div id="subnets-table-wrap">
      <div class="data-table">
        <table>
          <thead><tr><th>Netuid</th><th>Name</th><th>Blocks Since</th><th>Max N</th><th>Min Stake</th><th>Emission</th><th>Difficulty</th><th>Registry</th></tr></thead>
          <tbody id="subnets-rows"><tr><td colspan="8" class="loading">Loading</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div id="panel-delegates" class="panel">
    <h2>Delegates</h2>
    <p class="subtitle">All registered delegates on the Bittensor network</p>
    <div class="search-wrap">
      <input type="text" id="delegate-filter" placeholder="Filter by name or address" />
      <button onclick="loadDelegates()">Refresh</button>
    </div>
    <div id="delegates-table-wrap">
      <div class="data-table">
        <table>
          <thead><tr><th>Name</th><th>Address</th><th>Delegates</th><th>apr</th><th>take</th><th>trust</th><th>image</th><th>url</th></tr></thead>
          <tbody id="delegates-rows"><tr><td colspan="8" class="loading">Loading</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div id="panel-admin" class="panel">
    <h2>Admin Panel</h2>
    <p class="subtitle">API key management and service statistics</p>
    <div class="kpi-grid">
      <div class="kpi"><div class="label">Total Requests</div><div class="value blue" id="admin-total-req">—</div></div>
      <div class="kpi"><div class="label">Avg Response</div><div class="value green" id="admin-avg-ms">—</div><div class="sub">milliseconds</div></div>
      <div class="kpi"><div class="label">Active Keys</div><div class="value purple" id="admin-active-keys">—</div><div class="sub">of <span id="admin-total-keys">—</span> total</div></div>
    </div>
    <div class="detail-panel" style="margin-bottom:16px">
      <h3>API Keys</h3>
      <div class="search-wrap" style="margin-bottom:12px">
        <input type="text" id="new-key-name" placeholder="New key name" />
        <button onclick="createKey()">+ Create Key</button>
        <button class="btn-secondary" onclick="loadAdmin()">Refresh</button>
      </div>
      <div class="data-table">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Prefix</th><th>Admin</th><th>Active</th><th>Queries</th><th>Created</th><th>Last Used</th><th>Actions</th></tr></thead>
          <tbody id="admin-keys-rows"><tr><td colspan="9" class="loading">Loading</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</main>
<script>
const API = "{api_base}";
let apiToken = "";
"""
    tail = """
</script>
</body>
</html>"""

    return HTMLResponse(content=head + js + tail, status_code=200)
