# ruff: noqa: E501

from __future__ import annotations

from html import escape


def render_operator_console(app_name: str, operator: dict[str, object] | None) -> str:
    operator_name = escape(str((operator or {}).get("display_name") or "Operator"))
    operator_email = escape(str((operator or {}).get("email") or ""))
    safe_app_name = escape(app_name)
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_app_name}</title>
    <style>
      :root {{
        --bg: #f5efe4;
        --paper: #fffdf8;
        --panel: rgba(255, 253, 248, 0.88);
        --ink: #1f2937;
        --muted: #6b7280;
        --line: rgba(31, 41, 55, 0.12);
        --accent: #b45309;
        --accent-strong: #92400e;
        --success: #166534;
        --warning: #b45309;
        --danger: #b42318;
        --shadow: 0 20px 60px rgba(31, 41, 55, 0.14);
        --radius: 18px;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(245, 158, 11, 0.18), transparent 28%),
          radial-gradient(circle at top right, rgba(14, 116, 144, 0.16), transparent 24%),
          linear-gradient(180deg, #fbf6ea 0%, #f3ebde 45%, #eee5d4 100%);
      }}
      .shell {{
        max-width: 1440px;
        margin: 0 auto;
        padding: 28px 20px 48px;
      }}
      .topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 22px;
      }}
      .brand h1 {{
        margin: 0;
        font-size: 2rem;
        letter-spacing: -0.04em;
      }}
      .brand p {{
        margin: 8px 0 0;
        color: var(--muted);
        max-width: 760px;
      }}
      .operator-badge {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.65);
        box-shadow: var(--shadow);
      }}
      .operator-badge strong {{
        display: block;
      }}
      .operator-badge span {{
        color: var(--muted);
        font-size: 0.9rem;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(12, minmax(0, 1fr));
        gap: 18px;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        backdrop-filter: blur(14px);
        padding: 18px;
      }}
      .hero {{
        grid-column: span 12;
        display: grid;
        grid-template-columns: 1.6fr 1fr 1fr;
        gap: 18px;
      }}
      .section-title {{
        margin: 0 0 14px;
        font-size: 1.05rem;
        letter-spacing: -0.03em;
      }}
      .subtle {{
        color: var(--muted);
      }}
      .control-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: end;
      }}
      .field {{
        display: grid;
        gap: 6px;
        min-width: 120px;
        flex: 1 1 0;
      }}
      .field label {{
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      input,
      select,
      button,
      textarea {{
        font: inherit;
      }}
      input,
      select {{
        width: 100%;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.88);
        padding: 11px 12px;
        color: var(--ink);
      }}
      button {{
        border: none;
        border-radius: 999px;
        padding: 11px 16px;
        font-weight: 700;
        cursor: pointer;
        transition: transform 120ms ease, opacity 120ms ease;
      }}
      button:hover {{
        transform: translateY(-1px);
      }}
      button:disabled {{
        opacity: 0.45;
        cursor: not-allowed;
        transform: none;
      }}
      .btn-primary {{
        background: linear-gradient(135deg, #c2410c, var(--accent));
        color: white;
      }}
      .btn-secondary {{
        background: rgba(31, 41, 55, 0.08);
        color: var(--ink);
      }}
      .btn-success {{
        background: linear-gradient(135deg, #15803d, var(--success));
        color: white;
      }}
      .btn-danger {{
        background: linear-gradient(135deg, #dc2626, var(--danger));
        color: white;
      }}
      .stats {{
        display: grid;
        gap: 12px;
      }}
      .stat {{
        display: grid;
        gap: 3px;
        padding: 12px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid var(--line);
      }}
      .stat strong {{
        font-size: 1.4rem;
      }}
      .status-chip {{
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 0.84rem;
        font-weight: 700;
      }}
      .status-green {{
        background: rgba(22, 101, 52, 0.12);
        color: var(--success);
      }}
      .status-amber {{
        background: rgba(180, 83, 9, 0.12);
        color: var(--warning);
      }}
      .status-red {{
        background: rgba(180, 35, 24, 0.12);
        color: var(--danger);
      }}
      .status-gray {{
        background: rgba(31, 41, 55, 0.08);
        color: var(--ink);
      }}
      .main-grid {{
        margin-top: 18px;
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
        gap: 18px;
      }}
      .recommendation-list {{
        display: grid;
        gap: 16px;
      }}
      .recommendation-card {{
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.82);
        border-radius: 18px;
        padding: 18px;
      }}
      .recommendation-top {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: start;
      }}
      .recommendation-title {{
        margin: 0 0 8px;
        font-size: 1.22rem;
      }}
      .recommendation-meta {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin: 14px 0;
      }}
      .meta-box {{
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(255, 248, 240, 0.7);
      }}
      .meta-box strong {{
        display: block;
        margin-bottom: 4px;
        font-size: 0.82rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      .recommendation-actions {{
        display: grid;
        gap: 12px;
        margin-top: 14px;
      }}
      .action-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }}
      .detail-box,
      .positions-box,
      .console-box {{
        border: 1px solid var(--line);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.74);
        padding: 14px;
      }}
      .detail-box pre,
      .console-box pre {{
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 0.9rem;
      }}
      .positions-grid {{
        display: grid;
        gap: 14px;
      }}
      .position-item {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid rgba(31, 41, 55, 0.08);
      }}
      .position-item:last-child {{
        border-bottom: none;
      }}
      .toolbar {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }}
      .message {{
        position: sticky;
        top: 18px;
        z-index: 10;
        margin-bottom: 16px;
        padding: 13px 14px;
        border-radius: 16px;
        display: none;
        box-shadow: var(--shadow);
      }}
      .message.visible {{
        display: block;
      }}
      .message.info {{
        background: rgba(8, 145, 178, 0.12);
        color: #155e75;
      }}
      .message.success {{
        background: rgba(22, 101, 52, 0.14);
        color: var(--success);
      }}
      .message.error {{
        background: rgba(180, 35, 24, 0.14);
        color: var(--danger);
      }}
      @media (max-width: 1120px) {{
        .hero,
        .main-grid {{
          grid-template-columns: 1fr;
        }}
      }}
      @media (max-width: 720px) {{
        .topbar,
        .recommendation-top {{
          flex-direction: column;
          align-items: stretch;
        }}
        .recommendation-meta {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="shell">
      <div id="message" class="message"></div>
      <header class="topbar">
        <div class="brand">
          <h1>{safe_app_name}</h1>
          <p>
            Human-in-the-loop trading operations console. Scan symbols, inspect reasoning,
            approve trades, preview orders, execute on paper, and connect Zerodha.
          </p>
        </div>
        <div class="operator-badge">
          <div>
            <strong>{operator_name}</strong>
            <span>{operator_email}</span>
          </div>
          <button id="logout-button" class="btn-secondary" type="button">Log Out</button>
        </div>
      </header>

      <section class="hero">
        <article class="panel">
          <h2 class="section-title">Scan Market</h2>
          <div class="control-row">
            <div class="field">
              <label for="scan-symbol">Symbol</label>
              <input id="scan-symbol" value="INFY" />
            </div>
            <div class="field">
              <label for="scan-broker">Broker</label>
              <select id="scan-broker">
                <option value="PAPER">Paper</option>
                <option value="ZERODHA">Zerodha</option>
              </select>
            </div>
            <button id="scan-button" class="btn-primary" type="button">Run Scan</button>
            <button id="benchmark-button" class="btn-secondary" type="button">Benchmark</button>
          </div>
          <p class="subtle">
            Demo mode now produces actionable BUY and SELL ideas so the approval and execution
            paths can be tested end to end.
          </p>
        </article>

        <article class="panel">
          <h2 class="section-title">Broker Status</h2>
          <div id="zerodha-status" class="detail-box">Loading broker status...</div>
          <div class="toolbar" style="margin-top: 12px;">
            <button id="connect-zerodha" class="btn-primary" type="button">Connect Zerodha</button>
            <button id="disconnect-zerodha" class="btn-secondary" type="button">Disconnect</button>
            <button id="refresh-button" class="btn-secondary" type="button">Refresh</button>
          </div>
        </article>

        <article class="panel">
          <h2 class="section-title">Runtime Summary</h2>
          <div class="stats" id="stats-grid">
            <div class="stat"><span class="subtle">Recommendations</span><strong>0</strong></div>
            <div class="stat"><span class="subtle">Pending Approvals</span><strong>0</strong></div>
            <div class="stat"><span class="subtle">Executions</span><strong>0</strong></div>
          </div>
        </article>
      </section>

      <section class="main-grid">
        <article class="panel">
          <h2 class="section-title">Recommendations</h2>
          <div id="recommendation-list" class="recommendation-list">
            <div class="detail-box">Loading recommendations...</div>
          </div>
        </article>

        <aside class="panel">
          <h2 class="section-title">Positions</h2>
          <div class="positions-grid">
            <section class="positions-box">
              <h3 class="section-title">Paper Broker</h3>
              <div id="paper-positions">No positions yet.</div>
            </section>
            <section class="positions-box">
              <h3 class="section-title">Zerodha</h3>
              <div id="zerodha-positions">No positions yet.</div>
            </section>
            <section class="console-box">
              <h3 class="section-title">Replay / Benchmark Output</h3>
              <pre id="console-output">Run a scan or click Replay / Benchmark.</pre>
            </section>
          </div>
        </aside>
      </section>
    </div>

    <script>
      const state = {{
        bootstrap: null,
      }};

      const messageEl = document.getElementById("message");
      const recommendationListEl = document.getElementById("recommendation-list");
      const zerodhaStatusEl = document.getElementById("zerodha-status");
      const paperPositionsEl = document.getElementById("paper-positions");
      const zerodhaPositionsEl = document.getElementById("zerodha-positions");
      const consoleOutputEl = document.getElementById("console-output");
      const statsGridEl = document.getElementById("stats-grid");

      function showMessage(kind, text) {{
        messageEl.className = `message visible ${{kind}}`;
        messageEl.textContent = text;
      }}

      function clearMessage() {{
        messageEl.className = "message";
        messageEl.textContent = "";
      }}

      async function fetchJson(url, options = {{}}) {{
        const response = await fetch(url, {{
          credentials: "same-origin",
          headers: {{
            "content-type": "application/json",
            ...(options.headers || {{}}),
          }},
          ...options,
        }});
        let payload = null;
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {{
          payload = await response.json();
        }} else {{
          payload = await response.text();
        }}
        if (!response.ok) {{
          const detail = typeof payload === "object" && payload ? payload.detail || JSON.stringify(payload) : payload;
          throw new Error(detail || `Request failed with ${{response.status}}`);
        }}
        return payload;
      }}

      function statusClass(value) {{
        if (["APPROVED", "FILLED", "SUCCESS", "CONNECTED", "BUY"].includes(value)) {{
          return "status-green";
        }}
        if (["PENDING", "REVIEW", "HOLD", "EXPIRED"].includes(value)) {{
          return "status-amber";
        }}
        if (["REJECTED", "FAILED", "SELL"].includes(value)) {{
          return "status-red";
        }}
        return "status-gray";
      }}

      function chip(value) {{
        return `<span class="status-chip ${{statusClass(value)}}">${{value}}</span>`;
      }}

      function renderStats(items) {{
        const approvals = items.filter((item) => item.approval?.status === "PENDING").length;
        const executions = items.filter((item) => item.execution).length;
        statsGridEl.innerHTML = `
          <div class="stat"><span class="subtle">Recommendations</span><strong>${{items.length}}</strong></div>
          <div class="stat"><span class="subtle">Pending Approvals</span><strong>${{approvals}}</strong></div>
          <div class="stat"><span class="subtle">Executions</span><strong>${{executions}}</strong></div>
        `;
      }}

      function renderPositions(target, positions) {{
        if (!positions.length) {{
          target.innerHTML = "<div class='subtle'>No open positions.</div>";
          return;
        }}
        target.innerHTML = positions
          .map(
            (position) => `
              <div class="position-item">
                <div>
                  <strong>${{position.symbol}}</strong>
                  <div class="subtle">Qty ${{position.quantity}} at ${{position.average_price}}</div>
                </div>
                <div style="text-align:right;">
                  <strong>${{position.market_price}}</strong>
                  <div class="subtle">PnL ${{position.unrealized_pnl}}</div>
                </div>
              </div>
            `,
          )
          .join("");
      }}

      function renderZerodha(status) {{
        const connected = status.connected ? "CONNECTED" : "NOT_CONNECTED";
        const session = status.session;
        const identity = session
          ? `<div><strong>${{session.user_name || session.user_id || "Connected"}}</strong><div class="subtle">${{session.email || ""}}</div></div>`
          : "<div class='subtle'>No active Zerodha session. Use Connect Zerodha to start the Kite flow.</div>";
        zerodhaStatusEl.innerHTML = `
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
            <div>${{identity}}</div>
            ${{chip(connected)}}
          </div>
          <div class="subtle" style="margin-top:10px;">
            Login URL: ${{status.login_url ? `<code>${{status.login_url}}</code>` : "Not configured"}}
          </div>
        `;
      }}

      function recommendationControls(item) {{
        const recommendation = item.recommendation;
        const approval = item.approval || {{}};
        const actionBlocked = recommendation.action === "HOLD";
        const approvalReady = approval.status === "APPROVED";
        const token = approval.token || "";
        const brokerOptions = `
          <option value="PAPER">Paper</option>
          <option value="ZERODHA">Zerodha</option>
        `;
        return `
          <div class="action-row">
            <div class="field">
              <label for="quantity-${{recommendation.recommendation_id}}">Qty</label>
              <input id="quantity-${{recommendation.recommendation_id}}" type="number" min="1" value="1" />
            </div>
            <div class="field">
              <label for="broker-${{recommendation.recommendation_id}}">Broker</label>
              <select id="broker-${{recommendation.recommendation_id}}">${{brokerOptions}}</select>
            </div>
            <div class="field">
              <label for="order-${{recommendation.recommendation_id}}">Order Type</label>
              <select id="order-${{recommendation.recommendation_id}}">
                <option value="LIMIT">Limit</option>
                <option value="MARKET">Market</option>
                <option value="STOP">Stop</option>
              </select>
            </div>
          </div>
          <div class="action-row">
            <button class="btn-success" type="button"
              onclick="approveRecommendation('${{recommendation.recommendation_id}}', '${{token}}')"
              ${{approval.status !== "PENDING" ? "disabled" : ""}}>
              Approve
            </button>
            <button class="btn-danger" type="button"
              onclick="rejectRecommendation('${{recommendation.recommendation_id}}', '${{token}}')"
              ${{approval.status !== "PENDING" ? "disabled" : ""}}>
              Reject
            </button>
            <button class="btn-secondary" type="button"
              onclick="previewOrder('${{recommendation.recommendation_id}}', '${{token}}')">
              Preview
            </button>
            <button class="btn-primary" type="button"
              onclick="submitOrder('${{recommendation.recommendation_id}}', '${{token}}')"
              ${{actionBlocked ? "disabled" : ""}}>
              Submit
            </button>
          </div>
          <div class="action-row">
            <button class="btn-secondary" type="button"
              onclick="showWhy('${{recommendation.recommendation_id}}')">
              Why
            </button>
            <button class="btn-secondary" type="button"
              onclick="showRisk('${{recommendation.recommendation_id}}')">
              Risk
            </button>
            <button class="btn-secondary" type="button"
              onclick="showReplay('${{recommendation.run_id}}')">
              Replay
            </button>
          </div>
          <div class="subtle">
            Approval token: <code>${{token || "pending"}}</code>
            ${{approvalReady ? " · Ready for non-paper execution." : ""}}
            ${{actionBlocked ? " · HOLD recommendations cannot be submitted." : ""}}
          </div>
          <div id="detail-${{recommendation.recommendation_id}}" class="detail-box">
            <pre>${{escapeForHtml(recommendation.explanation?.why_this_trade || recommendation.thesis || "No explanation available.")}}</pre>
          </div>
        `;
      }}

      function renderRecommendations(items) {{
        if (!items.length) {{
          recommendationListEl.innerHTML =
            "<div class='detail-box'>No recommendations yet. Run a scan to populate the console.</div>";
          return;
        }}
        recommendationListEl.innerHTML = items
          .map((item) => {{
            const recommendation = item.recommendation;
            const approval = item.approval || {{}};
            const risk = item.risk || {{}};
            const execution = item.execution || {{}};
            const why = recommendation.explanation?.why_this_trade || recommendation.thesis || "No explanation available.";
            return `
              <article class="recommendation-card">
                <div class="recommendation-top">
                  <div>
                    <h3 class="recommendation-title">
                      ${{recommendation.symbol}} · ${{chip(recommendation.action)}}
                    </h3>
                    <div class="subtle">
                      Strategy: ${{recommendation.strategy_name}} · Confidence: ${{Math.round(recommendation.confidence * 100)}}%
                    </div>
                  </div>
                  <div>${{chip(execution.status || "N/A")}}</div>
                </div>
                <p>${{escapeForHtml(why)}}</p>
                <div class="recommendation-meta">
                  <div class="meta-box">
                    <strong>Risk</strong>
                    <div>${{chip(risk.decision || "N/A")}}</div>
                    <div class="subtle">${{escapeForHtml(risk.summary || "No risk evaluation")}}</div>
                  </div>
                  <div class="meta-box">
                    <strong>Approval</strong>
                    <div>${{chip(approval.status || "N/A")}}</div>
                    <div class="subtle">Broker: ${{approval.broker || "PAPER"}}</div>
                  </div>
                  <div class="meta-box">
                    <strong>Execution</strong>
                    <div>${{chip(execution.status || "N/A")}}</div>
                    <div class="subtle">${{escapeForHtml(execution.message || "Not executed")}}</div>
                  </div>
                  <div class="meta-box">
                    <strong>Reference</strong>
                    <div><code>${{recommendation.recommendation_id}}</code></div>
                    <div class="subtle">Run: <code>${{recommendation.run_id || "-"}}</code></div>
                  </div>
                </div>
                <div class="recommendation-actions">
                  ${{recommendationControls(item)}}
                </div>
              </article>
            `;
          }})
          .join("");
      }}

      function escapeForHtml(value) {{
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;");
      }}

      async function loadBootstrap() {{
        try {{
          clearMessage();
          const payload = await fetchJson("/v1/dashboard/bootstrap", {{
            headers: {{}},
          }});
          state.bootstrap = payload;
          renderStats(payload.recommendations);
          renderRecommendations(payload.recommendations);
          renderZerodha(payload.zerodha);
          renderPositions(paperPositionsEl, payload.positions.paper);
          renderPositions(zerodhaPositionsEl, payload.positions.zerodha);
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function scanSymbol() {{
        const symbol = document.getElementById("scan-symbol").value.trim().toUpperCase();
        const broker = document.getElementById("scan-broker").value;
        if (!symbol) {{
          showMessage("error", "Enter a symbol before scanning.");
          return;
        }}
        showMessage("info", `Scanning ${{symbol}} on ${{broker}}...`);
        try {{
          const payload = await fetchJson(`/v1/scan/${{symbol}}?broker=${{broker}}`);
          const recommendation = payload.recommendations[0];
          showMessage(
            "success",
            `${{symbol}} scanned. Top action: ${{recommendation.action}} at ${{Math.round(recommendation.confidence * 100)}}%.`,
          );
          await loadBootstrap();
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function benchmarkSymbol() {{
        const symbol = document.getElementById("scan-symbol").value.trim().toUpperCase();
        if (!symbol) {{
          showMessage("error", "Enter a symbol before benchmarking.");
          return;
        }}
        try {{
          const payload = await fetchJson(`/v1/benchmark/${{symbol}}`);
          consoleOutputEl.textContent = JSON.stringify(payload, null, 2);
          showMessage("success", `Benchmark loaded for ${{symbol}}.`);
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      function orderPayload(recommendationId, approvalToken) {{
        const quantity = Number(document.getElementById(`quantity-${{recommendationId}}`).value || "1");
        const broker = document.getElementById(`broker-${{recommendationId}}`).value;
        const orderType = document.getElementById(`order-${{recommendationId}}`).value;
        return {{
          recommendation_id: recommendationId,
          broker,
          quantity,
          order_type: orderType,
          approval_token: broker === "PAPER" ? null : approvalToken || null,
        }};
      }}

      async function approveRecommendation(recommendationId, token) {{
        try {{
          await fetchJson(
            `/v1/recommendations/${{recommendationId}}/approve?token=${{encodeURIComponent(token)}}`,
            {{ method: "POST" }},
          );
          showMessage("success", `Approved ${{recommendationId}}.`);
          await loadBootstrap();
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function rejectRecommendation(recommendationId, token) {{
        try {{
          await fetchJson(
            `/v1/recommendations/${{recommendationId}}/reject?token=${{encodeURIComponent(token)}}`,
            {{ method: "POST" }},
          );
          showMessage("success", `Rejected ${{recommendationId}}.`);
          await loadBootstrap();
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function previewOrder(recommendationId, token) {{
        try {{
          const payload = await fetchJson("/v1/orders/preview", {{
            method: "POST",
            body: JSON.stringify(orderPayload(recommendationId, token)),
          }});
          document.getElementById(`detail-${{recommendationId}}`).innerHTML =
            `<pre>${{escapeForHtml(JSON.stringify(payload, null, 2))}}</pre>`;
          showMessage("success", `Order preview generated for ${{recommendationId}}.`);
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function submitOrder(recommendationId, token) {{
        try {{
          const payload = await fetchJson("/v1/orders/submit", {{
            method: "POST",
            body: JSON.stringify(orderPayload(recommendationId, token)),
          }});
          document.getElementById(`detail-${{recommendationId}}`).innerHTML =
            `<pre>${{escapeForHtml(JSON.stringify(payload, null, 2))}}</pre>`;
          showMessage("success", `Order submitted for ${{recommendationId}}.`);
          await loadBootstrap();
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      function showWhy(recommendationId) {{
        const item = (state.bootstrap?.recommendations || []).find(
          (candidate) => candidate.recommendation.recommendation_id === recommendationId,
        );
        if (!item) {{
          return;
        }}
        const explanation = item.recommendation.explanation || {{}};
        document.getElementById(`detail-${{recommendationId}}`).innerHTML =
          `<pre>${{escapeForHtml(JSON.stringify(explanation, null, 2))}}</pre>`;
      }}

      function showRisk(recommendationId) {{
        const item = (state.bootstrap?.recommendations || []).find(
          (candidate) => candidate.recommendation.recommendation_id === recommendationId,
        );
        if (!item) {{
          return;
        }}
        document.getElementById(`detail-${{recommendationId}}`).innerHTML =
          `<pre>${{escapeForHtml(JSON.stringify(item.risk || {{}}, null, 2))}}</pre>`;
      }}

      async function showReplay(runId) {{
        if (!runId) {{
          showMessage("error", "Replay is not available because the run id is missing.");
          return;
        }}
        try {{
          const payload = await fetchJson(`/v1/replay/${{runId}}`);
          consoleOutputEl.textContent = JSON.stringify(payload, null, 2);
          showMessage("success", `Replay loaded for run ${{runId}}.`);
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      async function logout() {{
        await fetchJson("/v1/auth/logout", {{ method: "POST" }});
        window.location.reload();
      }}

      async function disconnectZerodha() {{
        try {{
          await fetchJson("/v1/brokers/zerodha/disconnect", {{ method: "POST" }});
          showMessage("success", "Zerodha disconnected.");
          await loadBootstrap();
        }} catch (error) {{
          showMessage("error", error.message);
        }}
      }}

      document.getElementById("scan-button").addEventListener("click", scanSymbol);
      document.getElementById("benchmark-button").addEventListener("click", benchmarkSymbol);
      document.getElementById("refresh-button").addEventListener("click", loadBootstrap);
      document
        .getElementById("connect-zerodha")
        .addEventListener("click", () => window.location.assign("/v1/brokers/zerodha/login"));
      document.getElementById("disconnect-zerodha").addEventListener("click", disconnectZerodha);
      document.getElementById("logout-button").addEventListener("click", logout);
      window.approveRecommendation = approveRecommendation;
      window.rejectRecommendation = rejectRecommendation;
      window.previewOrder = previewOrder;
      window.submitOrder = submitOrder;
      window.showWhy = showWhy;
      window.showRisk = showRisk;
      window.showReplay = showReplay;
      loadBootstrap();
      setInterval(loadBootstrap, 30000);
    </script>
  </body>
</html>
""".strip()
