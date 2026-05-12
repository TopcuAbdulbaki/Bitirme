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
    input, select, textarea, button {
      min-height: 42px;
      border-radius: 6px;
      border: 1px solid var(--line);
      padding: 0 12px;
      font: inherit;
    }
    input, select, textarea { flex: 1 1 220px; background: #fff; }
    textarea {
      min-height: 92px;
      padding: 10px 12px;
      resize: vertical;
      width: 100%;
    }
    button {
      cursor: pointer;
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 700;
    }
    button.secondary {
      border-color: var(--line);
      background: #fff;
      color: var(--text);
    }
    .control-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      width: 100%;
    }
    .field {
      display: grid;
      gap: 5px;
      min-width: 0;
    }
    .field span, .checkline {
      color: var(--muted);
      font-size: 12px;
    }
    .checkline {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 42px;
    }
    .checkline input {
      flex: 0 0 auto;
      min-height: 0;
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
        <div class="control-grid">
          <label class="field"><span>Makale limiti</span><input id="research-max-articles" type="number" min="1" max="100" value="10"></label>
          <label class="field"><span>Arama limiti</span><input id="research-max-searches" type="number" min="1" max="100" value="20"></label>
          <label class="field"><span>Dongu limiti</span><input id="research-max-cycles" type="number" min="1" max="50" value="12"></label>
          <label class="field"><span>Model adi</span><input id="research-model-name" placeholder="Qwen/Qwen3.5-9B"></label>
          <label class="field"><span>Context</span><input id="research-context-window" type="number" min="1024" step="1024" placeholder="32768"></label>
        </div>
        <button type="submit">Task Bas</button>
      </form>
      <p id="research-feedback" class="muted" style="margin-top:10px;"></p>
    </section>

    <section>
      <h2>Crawler Kontrolu</h2>
      <form id="crawl-form">
        <textarea id="crawl-urls" placeholder="bbc.com&#10;https://www.reuters.com/world/"></textarea>
        <div class="control-grid">
          <label class="checkline"><input id="crawl-use-defaults" type="checkbox" checked> Default kaynaklari da kullan</label>
          <label class="field"><span>Maksimum haber</span><input id="crawl-max-items" type="number" min="1" max="500" placeholder="Bos birak: limitsiz"></label>
          <label class="field"><span>Arama terimi</span><input id="crawl-search-query" value="Turkey OR Türkiye OR Turkiye"></label>
          <label class="field"><span>Zaman birimi</span>
            <select id="crawl-time-unit">
              <option value="h">Saat</option>
              <option value="d">Gun</option>
              <option value="w">Hafta</option>
              <option value="m">Ay</option>
            </select>
          </label>
          <label class="field"><span>Zaman degeri</span><input id="crawl-time-value" type="number" min="1" value="12"></label>
          <label class="field"><span>Maksimum gorsel</span><input id="crawl-max-images" type="number" min="1" max="10" value="3"></label>
          <label class="field"><span>Zorunlu kelimeler</span><input id="crawl-required-keywords" value="turkey,türkiye,turkiye,ankara,istanbul,turkish"></label>
        </div>
        <button type="submit">Crawler Baslat</button>
        <button id="crawl-stop" class="secondary" type="button">Durdur</button>
      </form>
      <p id="crawl-feedback" class="muted" style="margin-top:10px;"></p>
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
        <div class="control-grid">
          <label class="field"><span>Arama alani</span>
            <select id="search-area">
              <option value="all">Her yerde ara</option>
              <option value="text">Metinlerde ara</option>
              <option value="images">Gorsellerde ara</option>
            </select>
          </label>
          <label class="field"><span>Sentiment</span>
            <select id="search-sentiment">
              <option value="">Hepsi</option>
              <option value="1">Olumlu (1)</option>
              <option value="0">Notr (0)</option>
              <option value="-1">Olumsuz (-1)</option>
            </select>
          </label>
          <label class="field"><span>Baslangic</span><input id="search-date-from" type="date"></label>
          <label class="field"><span>Bitis</span><input id="search-date-to" type="date"></label>
          <label class="field"><span>Limit</span><input id="search-limit" type="number" min="1" max="50" value="12"></label>
        </div>
        <button type="submit">Ara</button>
      </form>
      <p id="search-mode" class="muted" style="margin-top:10px;"></p>
      <div id="search-results"></div>
      <pre id="news-detail" style="display:none;"></pre>
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
        ["Crawler", data.crawl.active ? "aktif" : "beklemede"],
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
      const queueCards = Object.entries(data.queues || {}).map(([label, value]) => `
        <div class="card">
          <div class="label">Queue ${esc(label)}</div>
          <div class="value">${esc(value ?? "-")}</div>
        </div>
      `);
      document.querySelector("#health-grid").innerHTML = health.map(([label, value]) => `
        <div class="card">
          <div class="label">${esc(label)}</div>
          <div class="status ${statusClass(value)}">${esc(value)}</div>
        </div>
      `).concat(queueCards).join("");
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
        const payload = {
          query,
          max_articles: Number(document.querySelector("#research-max-articles").value || 10),
          max_searches: Number(document.querySelector("#research-max-searches").value || 20),
          max_cycles: Number(document.querySelector("#research-max-cycles").value || 12),
          model_name: document.querySelector("#research-model-name").value.trim(),
          context_window: document.querySelector("#research-context-window").value.trim()
        };
        const data = await getJson("/api/research", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        feedback.textContent = data.queued ? "Task agent_tasks kuyruğuna basildi." : "Idle CUA bulunamadi veya publish olmadi.";
        await refreshSummary();
      } catch (error) {
        feedback.textContent = "Hata: " + error.message;
      }
    });
    document.querySelector("#crawl-form").addEventListener("submit", async event => {
      event.preventDefault();
      const feedback = document.querySelector("#crawl-feedback");
      feedback.textContent = "Crawler gorevi hazirlaniyor...";
      try {
        const payload = {
          urls: document.querySelector("#crawl-urls").value,
          use_default_sources: document.querySelector("#crawl-use-defaults").checked,
          max_items: document.querySelector("#crawl-max-items").value,
          search_query: document.querySelector("#crawl-search-query").value,
          time_unit: document.querySelector("#crawl-time-unit").value,
          time_value: document.querySelector("#crawl-time-value").value,
          max_images: document.querySelector("#crawl-max-images").value,
          required_keywords: document.querySelector("#crawl-required-keywords").value
        };
        const data = await getJson("/api/crawl/start", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload)
        });
        const targetCount = data.urls?.length || 0;
        feedback.textContent = `Crawler acildi. Ozel hedef: ${targetCount}, default: ${data.use_default_sources ? "evet" : "hayir"}.`;
      } catch (error) {
        feedback.textContent = "Hata: " + error.message;
      }
    });
    document.querySelector("#crawl-stop").addEventListener("click", async () => {
      const feedback = document.querySelector("#crawl-feedback");
      feedback.textContent = "Durduruluyor...";
      try {
        await getJson("/api/crawl/stop", {method: "POST"});
        feedback.textContent = "Crawler bekleyen gorevi kapatildi.";
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
        const params = new URLSearchParams({
          q: document.querySelector("#search-query").value.trim(),
          area: document.querySelector("#search-area").value,
          sentiment: document.querySelector("#search-sentiment").value,
          date_from: document.querySelector("#search-date-from").value,
          date_to: document.querySelector("#search-date-to").value,
          limit: document.querySelector("#search-limit").value || "12"
        });
        const data = await getJson(`/api/search?${params.toString()}`);
        mode.textContent = data.vector_search?.enabled
          ? "Metin + vektor arama aktif."
          : "Metin arama aktif, vektor arama bu ortamda kapali.";
        root.innerHTML = data.results.length ? data.results.map(item => `
          <article class="result">
            <strong>${esc(item.source || "Kaynak")} · ${esc(item.news_id)}</strong>
            <div>${esc(item.summary || item.excerpt || "")}</div>
            <div class="scoreline">
              ${esc(item.url || "")}<br>
              area=${esc(item.matched_area)} sentiment=${esc(item.sentiment_label ?? item.sentiment ?? "-")}
              date=${esc(item.scraped_at || item.stored_at || "-")}
              combined=${esc(item.combined_score)} text=${esc(item.text_score)} image=${esc(item.image_score)} vector=${esc(item.vector_score)}
            </div>
            <button class="secondary" type="button" onclick="showNews('${esc(item.news_id)}')">Tam Haber</button>
          </article>
        `).join("") : `<div class="empty">Sonuc yok</div>`;
      } catch (error) {
        mode.textContent = "";
        root.innerHTML = `<div class="empty">Hata: ${esc(error.message)}</div>`;
      }
    });
    async function showNews(newsId) {
      const panel = document.querySelector("#news-detail");
      panel.style.display = "block";
      panel.textContent = "Yukleniyor...";
      try {
        const data = await getJson(`/api/news/${encodeURIComponent(newsId)}`);
        panel.textContent = JSON.stringify(data.news || data, null, 2);
      } catch (error) {
        panel.textContent = "Hata: " + error.message;
      }
    }
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
        app.router.add_post("/api/crawl/start", self.crawl_start)
        app.router.add_post("/api/crawl/stop", self.crawl_stop)
        app.router.add_get("/api/search", self.search)
        app.router.add_get("/api/news/{news_id}", self.news_detail)
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
                "crawl": {
                    "active": self.orchestrator.crawl_active,
                    "urls": self.orchestrator._crawl_urls,
                    "config": self.orchestrator._crawl_config,
                },
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
        params = {
            "max_articles": int(payload.get("max_articles") or 10),
            "max_searches": int(payload.get("max_searches") or 20),
            "max_cycles": int(payload.get("max_cycles") or 12),
        }
        if payload.get("model_name"):
            params["model_name"] = str(payload.get("model_name")).strip()
        if payload.get("context_window"):
            params["context_window"] = str(payload.get("context_window")).strip()
        metadata = {
            "model_name": payload.get("model_name") or "",
            "context_window": payload.get("context_window") or "",
        }
        queued = bool(self.orchestrator.queue_research(query, params=params, metadata=metadata))
        return web.json_response({"queued": queued, "query": query})

    async def crawl_start(self, request):
        payload = await request.json()
        raw_urls = str(payload.get("urls") or "")
        urls = [
            item.strip()
            for item in raw_urls.replace(",", "\n").splitlines()
            if item.strip()
        ]
        use_default_sources = bool(payload.get("use_default_sources", True))
        max_items = payload.get("max_items")
        config = {}
        if max_items not in (None, ""):
            config["max_items"] = max(1, int(max_items))
        for key in ("search_query", "time_unit", "time_value", "max_images", "required_keywords"):
            value = payload.get(key)
            if value not in (None, ""):
                config[key] = value
        self.orchestrator.start_crawl(
            urls=urls,
            use_default_sources=use_default_sources,
            config=config,
        )
        return web.json_response(
            {
                "started": True,
                "urls": urls,
                "use_default_sources": use_default_sources,
                "config": config,
            }
        )

    async def crawl_stop(self, request):
        self.orchestrator.stop_crawl()
        return web.json_response({"stopped": True})

    async def search(self, request):
        query = request.query.get("q", "")
        limit = min(max(int(request.query.get("limit", "12")), 1), 50)
        return web.json_response(
            await self.db.search_news(
                query,
                limit=limit,
                sentiment=request.query.get("sentiment") or "",
                date_from=request.query.get("date_from") or "",
                date_to=request.query.get("date_to") or "",
                area=request.query.get("area") or "all",
            )
        )

    async def missions(self, request):
        limit = min(max(int(request.query.get("limit", "20")), 1), 100)
        return web.json_response(await self.db.list_missions(limit=limit))

    async def news_detail(self, request):
        return web.json_response(await self.db.news_detail(request.match_info["news_id"]))

    async def mission_detail(self, request):
        return web.json_response(await self.db.mission_detail(request.match_info["mission_id"]))
