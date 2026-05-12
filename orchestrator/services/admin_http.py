"""Local HTML ops panel and JSON admin API for the orchestrator."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from aiohttp import web

from .admin_db import AdminDatabase


INDEX_HTML = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bitirme Orchestrator</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --line: #d8dee9;
      --text: #162033;
      --muted: #5b6578;
      --accent: #1463ff;
      --ok: #0f8a5f;
      --warn: #c57a00;
      --bad: #b12a3a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 Arial, sans-serif;
    }
    main {
      width: min(1280px, calc(100vw - 32px));
      margin: 24px auto 40px;
      display: grid;
      gap: 18px;
    }
    header, section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 24px; }
    h2 { font-size: 16px; margin-bottom: 14px; }
    .topline, .grid, .toolbar, .stats, .split {
      display: grid;
      gap: 12px;
    }
    .topline { grid-template-columns: 1fr auto; align-items: center; }
    .grid { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .stats { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
    .split { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 82px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 24px; font-weight: 700; margin-top: 4px; }
    .status {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 0 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-weight: 700;
    }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    form, .searchbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    input, button {
      min-height: 42px;
      border-radius: 6px;
      border: 1px solid var(--line);
      padding: 0 12px;
      font: inherit;
    }
    input { flex: 1 1 280px; background: #fff; }
    button {
      cursor: pointer;
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 700;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      text-align: left;
      vertical-align: top;
      border-top: 1px solid var(--line);
      padding: 10px 8px;
      word-break: break-word;
    }
    th { color: var(--muted); font-weight: 700; border-top: 0; }
    .muted { color: var(--muted); }
    .result {
      border-top: 1px solid var(--line);
      padding: 12px 0;
      display: grid;
      gap: 6px;
    }
    .scoreline { color: var(--muted); font-size: 12px; }
    .empty { color: var(--muted); padding: 8px 0; }
    pre {
      margin: 8px 0 0;
      padding: 12px;
      border-radius: 8px;
      background: #111827;
      color: #dbeafe;
      overflow: auto;
      max-height: 360px;
    }
    @media (max-width: 720px) {
      main { width: calc(100vw - 20px); margin-top: 10px; }
      .topline { grid-template-columns: 1fr; }
      table { display: block; overflow-x: auto; }
    }
  </style>
</head>
<body>
  <main>
    <header class="topline">
      <div>
        <h1>Bitirme Orchestrator</h1>
        <p class="muted">Yerel operasyon paneli</p>
      </div>
      <div id="overall-health" class="status warn">Yukleniyor</div>
    </header>

    <section>
      <h2>Research Talebi</h2>
      <form id="research-form">
        <input id="research-query" placeholder="Turkey economy 2026" required>
        <button type="submit">Task Bas</button>
      </form>
      <p id="research-feedback" class="muted" style="margin-top:10px;"></p>
    </section>

    <section>
      <h2>Sistem Ozeti</h2>
      <div class="stats" id="summary-stats"></div>
      <div class="grid" id="health-grid" style="margin-top:12px;"></div>
    </section>

    <section>
      <h2>Nodelar</h2>
      <table>
        <thead>
          <tr><th>ID</th><th>Tip</th><th>Durum</th><th>Son Heartbeat</th><th>Aktif Task</th></tr>
        </thead>
        <tbody id="nodes-body"></tbody>
      </table>
    </section>

    <section class="split">
      <div>
        <h2>Pipeline Tasklari</h2>
        <table>
          <thead>
            <tr><th>ID</th><th>Stage</th><th>Hata</th></tr>
          </thead>
          <tbody id="tasks-body"></tbody>
        </table>
      </div>
      <div>
        <h2>Research Missionlari</h2>
        <div id="missions"></div>
      </div>
    </section>

    <section>
      <h2>DB Arama</h2>
      <form id="search-form" class="searchbar">
        <input id="search-query" placeholder="Enflasyon, enerji, diplomasi..." required>
        <button type="submit">Ara</button>
      </form>
      <p id="search-mode" class="muted" style="margin-top:10px;"></p>
      <div id="search-results"></div>
    </section>
  </main>
  <script>
    async function getJson(url, options) {
      const response = await fetch(url, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || response.statusText);
      return data;
    }
    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
      }[ch]));
    }
    function statusClass(value) {
      if (["IDLE", "ready", "connected", "ok"].includes(value)) return "ok";
      if (["BUSY", "degraded", "warning"].includes(value)) return "warn";
      return "bad";
    }
    async function refreshSummary() {
      const data = await getJson("/api/summary");
      const stats = [
        ["Nodes", data.nodes_total],
        ["Pending Tasks", data.pending_tasks],
        ["Haber", data.db_stats.total_news ?? "-"],
        ["Embedding %", data.db_stats.embedding_coverage ?? "-"],
        ["Pending VLM", data.db_stats.pending_vlm ?? "-"],
        ["Pending LLM", data.db_stats.pending_llm ?? "-"]
      ];
      document.querySelector("#summary-stats").innerHTML = stats.map(([label, value]) => `
        <div class="card"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>
      `).join("");
      const health = [
        ["gRPC", data.health.grpc ? "ok" : "bad"],
        ["RabbitMQ", data.health.rabbitmq ? "ok" : "bad"],
        ["DB", data.health.db.connected ? "ok" : "degraded"],
        ["Vector Search", data.health.db.vector_search?.enabled ? "ok" : "degraded"]
      ];
      document.querySelector("#health-grid").innerHTML = health.map(([label, value]) => `
        <div class="card">
          <div class="label">${esc(label)}</div>
          <div class="status ${statusClass(value)}">${esc(value)}</div>
        </div>
      `).join("");
      const overall = document.querySelector("#overall-health");
      overall.textContent = data.health.rabbitmq && data.health.grpc ? "Operasyonel" : "Degraded";
      overall.className = "status " + (data.health.rabbitmq && data.health.grpc ? "ok" : "warn");
      document.querySelector("#tasks-body").innerHTML = data.tasks.length ? data.tasks.map(task => `
        <tr><td>${esc(task.task_id)}</td><td>${esc(task.stage)}</td><td>${esc(task.error || "")}</td></tr>
      `).join("") : `<tr><td colspan="3" class="muted">Task yok</td></tr>`;
    }
    async function refreshNodes() {
      const data = await getJson("/api/nodes");
      document.querySelector("#nodes-body").innerHTML = data.nodes.length ? data.nodes.map(node => `
        <tr>
          <td>${esc(node.node_id)}</td>
          <td>${esc(node.node_type)}</td>
          <td><span class="status ${statusClass(node.status)}">${esc(node.status)}</span></td>
          <td>${esc(node.last_heartbeat)}</td>
          <td>${esc(node.current_task_id || "")}</td>
        </tr>
      `).join("") : `<tr><td colspan="5" class="muted">Node yok</td></tr>`;
    }
    async function refreshMissions() {
      const data = await getJson("/api/missions");
      const root = document.querySelector("#missions");
      if (!data.available) {
        root.innerHTML = `<div class="empty">DB unavailable: ${esc(data.error || "")}</div>`;
        return;
      }
      root.innerHTML = data.missions.length ? data.missions.map(mission => `
        <div class="result">
          <strong>${esc(mission.topic)}</strong>
          <div class="scoreline">${esc(mission.mission_id)} · ${esc(mission.status)} · ${esc(mission.created_at || "")}</div>
        </div>
      `).join("") : `<div class="empty">Mission yok</div>`;
    }
    document.querySelector("#research-form").addEventListener("submit", async event => {
      event.preventDefault();
      const feedback = document.querySelector("#research-feedback");
      feedback.textContent = "Task basiliyor...";
      try {
        const query = document.querySelector("#research-query").value.trim();
        const data = await getJson("/api/research", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query})
        });
        feedback.textContent = data.queued ? "Task agent_tasks kuyruğuna basildi." : "Idle CUA bulunamadi veya publish olmadi.";
        await refreshSummary();
      } catch (error) {
        feedback.textContent = "Hata: " + error.message;
      }
    });
    document.querySelector("#search-form").addEventListener("submit", async event => {
      event.preventDefault();
      const root = document.querySelector("#search-results");
      const mode = document.querySelector("#search-mode");
      root.innerHTML = `<div class="empty">Araniyor...</div>`;
      try {
        const query = encodeURIComponent(document.querySelector("#search-query").value.trim());
        const data = await getJson(`/api/search?q=${query}`);
        mode.textContent = data.vector_search?.enabled
          ? "Metin + vektor arama aktif."
          : "Metin arama aktif, vektor arama bu ortamda kapali.";
        root.innerHTML = data.results.length ? data.results.map(item => `
          <article class="result">
            <strong>${esc(item.source || "Kaynak")} · ${esc(item.news_id)}</strong>
            <div>${esc(item.summary || item.excerpt || "")}</div>
            <div class="scoreline">combined=${esc(item.combined_score)} text=${esc(item.text_score)} vector=${esc(item.vector_score)}</div>
          </article>
        `).join("") : `<div class="empty">Sonuc yok</div>`;
      } catch (error) {
        mode.textContent = "";
        root.innerHTML = `<div class="empty">Hata: ${esc(error.message)}</div>`;
      }
    });
    async function refreshAll() {
      await Promise.allSettled([refreshSummary(), refreshNodes(), refreshMissions()]);
    }
    refreshAll();
    setInterval(refreshAll, 5000);
  </script>
</body>
</html>
"""


class AdminHttpServer:
    """Aiohttp-backed local admin panel bound to the orchestrator lifecycle."""

    def __init__(self, orchestrator, host: str, port: int):
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self.db = AdminDatabase()
        self._runner = None
        self._site = None

    async def start(self):
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/api/summary", self.summary)
        app.router.add_get("/api/nodes", self.nodes)
        app.router.add_post("/api/research", self.research)
        app.router.add_get("/api/search", self.search)
        app.router.add_get("/api/missions", self.missions)
        app.router.add_get("/api/missions/{mission_id}", self.mission_detail)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        print(f"[AdminHTTP] Listening on http://{self.host}:{self.port}")

    async def stop(self):
        await self.db.close()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._site = None

    async def index(self, request):
        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def summary(self, request):
        db_health, db_stats = await self.db.health(), await self.db.stats()
        return web.json_response(
            {
                "nodes_total": len(self.orchestrator.registry),
                "pending_tasks": len(self.orchestrator.pipeline.get_pending_tasks()),
                "tasks": self.orchestrator.task_snapshot(limit=20),
                "queues": self.orchestrator.queue_snapshot(),
                "health": {
                    "grpc": self.orchestrator.grpc_ready,
                    "rabbitmq": self.orchestrator.rabbitmq is not None,
                    "db": db_health,
                },
                "db_stats": db_stats,
            }
        )

    async def nodes(self, request):
        return web.json_response({"nodes": self.orchestrator.node_snapshot()})

    async def research(self, request):
        payload = await request.json()
        query = str(payload.get("query", "")).strip()
        if not query:
            return web.json_response({"error": "query is required"}, status=400)
        queued = bool(self.orchestrator.queue_research(query))
        return web.json_response({"queued": queued, "query": query})

    async def search(self, request):
        query = request.query.get("q", "")
        limit = min(max(int(request.query.get("limit", "12")), 1), 50)
        return web.json_response(await self.db.search_news(query, limit=limit))

    async def missions(self, request):
        limit = min(max(int(request.query.get("limit", "20")), 1), 100)
        return web.json_response(await self.db.list_missions(limit=limit))

    async def mission_detail(self, request):
        return web.json_response(await self.db.mission_detail(request.match_info["mission_id"]))
