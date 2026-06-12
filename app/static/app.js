const form = document.querySelector("#analysisForm");
const sampleBtn = document.querySelector("#sampleBtn");
const previewLatestBtn = document.querySelector("#previewLatestBtn");
const copyBtn = document.querySelector("#copyBtn");
const queryInput = document.querySelector("#query");
const runState = document.querySelector("#runState");
const emptyState = document.querySelector("#emptyState");
const loadingState = document.querySelector("#loadingState");
const loadingText = document.querySelector("#loadingText");
const progressPercent = document.querySelector("#progressPercent");
const progressBar = document.querySelector("#progressBar");
const progressList = document.querySelector("#progressList");
const activityStream = document.querySelector("#activityStream");
const resultState = document.querySelector("#resultState");
const errorState = document.querySelector("#errorState");
const summaryGrid = document.querySelector("#summaryGrid");
const reportText = document.querySelector("#reportText");
const expandReportBtn = document.querySelector("#expandReportBtn");
const reportModal = document.querySelector("#reportModal");
const modalBackdrop = document.querySelector("#modalBackdrop");
const closeModalBtn = document.querySelector("#closeModalBtn");
const modalCopyBtn = document.querySelector("#modalCopyBtn");
const modalReportContent = document.querySelector("#modalReportContent");
const navLinks = document.querySelectorAll(".nav-link");
const pageViews = document.querySelectorAll(".page-view");
const kellyForm = document.querySelector("#kellyForm");
const kellySampleBtn = document.querySelector("#kellySampleBtn");
const kellyState = document.querySelector("#kellyState");
const kellyEmpty = document.querySelector("#kellyEmpty");
const kellyResult = document.querySelector("#kellyResult");
const kellyError = document.querySelector("#kellyError");
const recommendedAmount = document.querySelector("#recommendedAmount");
const kellyVerdict = document.querySelector("#kellyVerdict");
const riskCapital = document.querySelector("#riskCapital");
const maxLoss = document.querySelector("#maxLoss");
const positionUnits = document.querySelector("#positionUnits");
const exposurePct = document.querySelector("#exposurePct");
const rewardRisk = document.querySelector("#rewardRisk");
const appliedKelly = document.querySelector("#appliedKelly");
const stopLossPct = document.querySelector("#stopLossPct");
const takeProfitPct = document.querySelector("#takeProfitPct");
const tradeDirection = document.querySelector("#tradeDirection");
const kellyNotes = document.querySelector("#kellyNotes");
const eventTabs = document.querySelectorAll(".event-tab");
const eventsState = document.querySelector("#eventsState");
const refreshEventsBtn = document.querySelector("#refreshEventsBtn");
const eventsSummaryTitle = document.querySelector("#eventsSummaryTitle");
const eventsMeta = document.querySelector("#eventsMeta");
const eventsGrid = document.querySelector("#eventsGrid");
const eventsEmpty = document.querySelector("#eventsEmpty");
const eventsError = document.querySelector("#eventsError");
const eventsOverview = document.querySelector("#eventsOverview");
const eventFilters = document.querySelectorAll(".event-filter");
const dashboardMode = document.querySelector("#dashboardMode");
const dashboardDate = document.querySelector("#dashboardDate");
const dashboardStrategy = document.querySelector("#dashboardStrategy");
const recommendationState = document.querySelector("#recommendationState");
const recommendationList = document.querySelector("#recommendationList");
const watchlistItems = document.querySelector("#watchlistItems");
const dashboardReports = document.querySelector("#dashboardReports");
const recommendationDetail = document.querySelector("#recommendationDetail");
const detailSymbol = document.querySelector("#detailSymbol");
const detailName = document.querySelector("#detailName");
const detailSummary = document.querySelector("#detailSummary");
const detailMetrics = document.querySelector("#detailMetrics");
const detailReasons = document.querySelector("#detailReasons");
const detailRisks = document.querySelector("#detailRisks");
const detailInvalidations = document.querySelector("#detailInvalidations");
const detailWatchBtn = document.querySelector("#detailWatchBtn");
const detailNotifyBtn = document.querySelector("#detailNotifyBtn");
const priceChart = document.querySelector("#priceChart");
const notificationResult = document.querySelector("#notificationResult");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");
const chatMessages = document.querySelector("#chatMessages");
const chatMode = document.querySelector("#chatMode");
const systemStatusCards = document.querySelector("#systemStatusCards");
const testTushareBtn = document.querySelector("#testTushareBtn");
const refreshTushareBtn = document.querySelector("#refreshTushareBtn");
const dataSourceState = document.querySelector("#dataSourceState");
const dataSourceMeta = document.querySelector("#dataSourceMeta");
const dataSourceMessage = document.querySelector("#dataSourceMessage");
const top20State = document.querySelector("#top20State");
const top20List = document.querySelector("#top20List");
const watchSearchForm = document.querySelector("#watchSearchForm");
const watchSearchInput = document.querySelector("#watchSearchInput");
const watchSearchResults = document.querySelector("#watchSearchResults");
const trackedStocks = document.querySelector("#trackedStocks");
const trackedCount = document.querySelector("#trackedCount");
const trackingDetail = document.querySelector("#trackingDetail");
const trackingDetailSymbol = document.querySelector("#trackingDetailSymbol");
const trackingDetailName = document.querySelector("#trackingDetailName");
const trackingDetailSummary = document.querySelector("#trackingDetailSummary");
const trackingMetrics = document.querySelector("#trackingMetrics");
const trackingChart = document.querySelector("#trackingChart");
const trackingFactors = document.querySelector("#trackingFactors");
const trackingRemoveBtn = document.querySelector("#trackingRemoveBtn");

let pollingTimer = null;
let currentReportPlainText = "";
let currentEventMarket = "a_share";
let currentEventFilter = "all";
let currentEventPayload = null;
let currentRecommendation = null;
let dashboardLoaded = false;
let portfolioLoaded = false;
let currentTrackingSymbol = null;
let currentTrackingInWatchlist = false;

function selectedValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`)?.value;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 2
  }).format(Number(value || 0));
}

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits
  }).format(Number(value || 0));
}

function formatPercent(value) {
  return `${formatNumber(Number(value || 0) * 100, 2)}%`;
}

function formatSignedPercent(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${formatNumber(number, 2)}%`;
}

function setView(view) {
  emptyState.classList.toggle("hidden", view !== "empty");
  loadingState.classList.toggle("hidden", view !== "loading");
  resultState.classList.toggle("hidden", view !== "result");
  errorState.classList.toggle("hidden", view !== "error");
}

function stopPolling() {
  if (pollingTimer) {
    window.clearTimeout(pollingTimer);
    pollingTimer = null;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function valueFromPath(source, path) {
  return path.split(".").reduce((current, key) => {
    if (!current || typeof current !== "object") return "";
    return current[key] ?? "";
  }, source);
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "待确认";
  if (Array.isArray(value)) return value.map(displayValue).join(" / ");
  if (typeof value === "object") {
    const preferredKeys = ["preferred_range", "base", "rating", "conclusion", "summary", "value", "text"];
    for (const key of preferredKeys) {
      if (value[key]) return displayValue(value[key]);
    }
    return Object.entries(value)
      .slice(0, 3)
      .map(([key, val]) => `${key}: ${displayValue(val)}`)
      .join("；");
  }
  return String(value);
}

function renderProgress(task) {
  const currentStep = Math.max(0, Math.min(task.total_steps || 12, task.current_step || 0));
  const totalSteps = task.total_steps || 12;
  const percent = Math.round((currentStep / totalSteps) * 100);
  progressPercent.textContent = `${currentStep}/${totalSteps}`;
  progressBar.style.width = `${percent}%`;
  loadingText.textContent = task.current_message || "任务运行中";
  runState.textContent = task.status === "queued" ? "排队中" : "运行中";

  renderActivityStream(task.progress || []);

  progressList.innerHTML = (task.steps || [])
    .map((item) => {
      const notes = (item.notes || [])
        .slice(-3)
        .map((note) => `<p class="step-note">${escapeHtml(note)}</p>`)
        .join("");
      return `
        <li class="workflow-step ${item.status}">
          <div class="step-index">${item.step}</div>
          <div class="step-body">
            <div class="step-title-row">
              <strong>${escapeHtml(item.title)}</strong>
              <span>${stepStatusText(item.status)}</span>
            </div>
            <p class="step-description">${escapeHtml(item.description)}</p>
            ${notes ? `<div class="step-notes">${notes}</div>` : ""}
          </div>
        </li>
      `;
    })
    .join("");
}

function renderActivityStream(events) {
  if (!events.length) {
    activityStream.innerHTML = `
      <article class="activity-item active">
        <span></span>
        <div>
          <strong>等待后端确认</strong>
          <p>任务已提交，正在等待工作流线程启动。</p>
        </div>
      </article>
    `;
    return;
  }

  activityStream.innerHTML = events
    .slice(-12)
    .reverse()
    .map((event, index) => {
      const item = describeEvent(event.message);
      return `
        <article class="activity-item ${index === 0 ? "active" : ""}">
          <span></span>
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <p>${escapeHtml(item.detail)}</p>
          </div>
        </article>
      `;
    })
    .join("");
}

function describeEvent(message) {
  const analystNames = {
    "02_source_intelligence": "来源情报分析师",
    "03_fundamental_business": "基本面业务分析师",
    "04_financial_quality": "财务质量分析师",
    "05_dcf_intrinsic_value": "DCF 内在价值分析师",
    "06_relative_valuation": "相对估值分析师",
    "07_market_expectation_gap": "市场预期差分析师",
    "08_earnings_revision": "盈利预测修正分析师",
    "09_catalyst_event": "催化剂事件分析师",
    "10_industry_cycle": "行业周期分析师",
    "11_growth_emerging": "成长与新兴业务分析师",
    "12_technical_price_volume": "技术量价分析师",
    "13_sentiment_public_opinion": "市场情绪分析师",
    "14_risk_disconfirmation": "风险反证分析师",
    "01_final_synthesis": "最终综合负责人"
  };

  const stepMatch = message.match(/\[(\d+)\/12\]\s*(.*)/);
  if (stepMatch) {
    return {
      title: `进入第 ${stepMatch[1]} 步`,
      detail: translateStage(stepMatch[2] || message)
    };
  }

  const runningMatch = message.match(/running\s+([0-9a-z_]+)\s+with\s+(.+)/i);
  if (runningMatch) {
    const name = analystNames[runningMatch[1]] || runningMatch[1];
    return {
      title: `${name}开始工作`,
      detail: `正在调用 ${runningMatch[2]}，处理该节点需要的证据、假设和结构化输出。`
    };
  }

  const completedMatch = message.match(/completed\s+([0-9a-z_]+).*tokens=(\d+).*estimated_cost=\$([0-9.]+)/i);
  if (completedMatch) {
    return {
      title: `${analystNames[completedMatch[1]] || completedMatch[1]}输出完成`,
      detail: `本轮消耗 ${completedMatch[2]} tokens，估算成本 $${completedMatch[3]}。`
    };
  }

  const finishedMatch = message.match(/finished\s+([0-9a-z_]+)/i);
  if (finishedMatch) {
    return {
      title: `${analystNames[finishedMatch[1]] || finishedMatch[1]}完成`,
      detail: "该节点输出已回传，工作流正在合并上下文并推进下一个节点。"
    };
  }

  if (message.includes("external data collected")) {
    return { title: "外部数据采集完成", detail: message.trim() };
  }
  if (message.includes("search provider=")) {
    return { title: "搜索数据源确认", detail: message.trim() };
  }
  if (message.includes("data request finished")) {
    return { title: "数据需求节点完成", detail: message.trim() };
  }
  return { title: "工作流更新", detail: message.trim() };
}

function translateStage(stage) {
  const map = {
    "workflow started": "工作流已启动，正在识别任务边界和分析对象。",
    "analyst data request stage": "各分析师正在声明需要哪些数据和证据。",
    "02 requirement aggregation stage": "正在汇总所有数据需求，形成采集优先级。",
    "external data collection stage": "正在抓取行情、财务、搜索结果和用户材料。",
    "source intelligence annotation stage": "正在给证据来源做可靠性和覆盖度标注。",
    "parallel basic quality stage: 03/04/10/11": "基本面、财务质量、行业周期、成长性正在并行分析。",
    "earnings revision stage": "正在检查盈利预测和市场共识变化。",
    "parallel valuation stage: 05/06": "DCF 和相对估值正在并行计算与校验。",
    "parallel expectation and catalyst stage: 07/09": "正在识别市场预期差和潜在催化剂。",
    "parallel market confirmation stage: 12/13": "正在检查技术量价和市场情绪是否确认结论。",
    "risk disconfirmation stage": "正在从反证视角检查核心假设是否站得住。",
    "final synthesis stage": "正在综合所有分析师输出，形成最终估值判断。",
    "workflow completed": "全部节点完成，正在准备报告输出。"
  };
  return map[stage.trim()] || stage.trim();
}

function stepStatusText(status) {
  return {
    pending: "等待",
    running: "运行中",
    completed: "完成",
    failed: "失败"
  }[status] || status;
}

function renderSummary(data) {
  const task = data.task_brief || {};
  const lean = data.lean_report || {};
  const cost = data.cost_summary || {};
  const cards = [
    ["标的", task.company_name || task.ticker || "待确认"],
    ["状态", data.status || "unknown"],
    ["信息截止", task.information_cutoff || task.analysis_date || "当前运行日"],
    ["核心判断", valueFromPath(lean, "investment_conclusion.rating") || valueFromPath(lean, "conclusion") || "见报告正文"],
    ["估值区间", valueFromPath(lean, "valuation.fair_value_range") || valueFromPath(lean, "fair_value_range") || "见报告正文"],
    ["Token", cost.total_tokens || cost.total_token || "未返回"]
  ];

  summaryGrid.innerHTML = cards
    .map(([label, value]) => `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(displayValue(value))}</strong></div>`)
    .join("");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const html = [];
  let inList = false;

  function closeList() {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      continue;
    }

    const h3 = line.match(/^###\s+(.+)/);
    const h2 = line.match(/^##\s+(.+)/);
    const h1 = line.match(/^#\s+(.+)/);
    const bullet = line.match(/^[-*]\s+(.+)/);

    if (h1 || h2 || h3) {
      closeList();
      const level = h1 ? 2 : h2 ? 3 : 4;
      const text = h1?.[1] || h2?.[1] || h3?.[1];
      html.push(`<h${level}>${inlineMarkdown(text)}</h${level}>`);
    } else if (bullet) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inlineMarkdown(bullet[1])}</li>`);
    } else {
      closeList();
      html.push(`<p>${inlineMarkdown(line)}</p>`);
    }
  }

  closeList();
  return html.join("");
}

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function renderResult(result) {
  renderSummary(result);
  const report = result.long_report || result.text_report || "";
  currentReportPlainText = report || "分析未生成报告，请补充明确的公司名称或股票代码后重试。";
  const renderedReport = renderMarkdown(currentReportPlainText);
  reportText.innerHTML = renderedReport;
  modalReportContent.innerHTML = renderedReport;
  runState.textContent = result.status === "refused" ? "需要补充信息" : "已完成";
  setView("result");
  form.querySelector(".primary").disabled = false;
}

function openReportModal() {
  if (!currentReportPlainText) return;
  reportModal.classList.remove("hidden");
  document.body.classList.add("modal-open");
  closeModalBtn.focus();
}

function closeReportModal() {
  reportModal.classList.add("hidden");
  document.body.classList.remove("modal-open");
}

async function pollTask(taskId) {
  const response = await fetch(`/api/analysis/${taskId}`);
  const task = await response.json();
  if (!response.ok) {
    throw new Error(task.detail || "无法读取任务状态");
  }

  renderProgress(task);

  if (task.status === "completed") {
    stopPolling();
    renderResult(task.result);
    return;
  }

  if (task.status === "failed") {
    stopPolling();
    runState.textContent = "失败";
    errorState.textContent = task.error || "分析任务失败，请检查 .env 配置和后端日志。";
    setView("error");
    form.querySelector(".primary").disabled = false;
    return;
  }

  pollingTimer = window.setTimeout(() => pollTask(taskId).catch(handleError), 1200);
}

function handleError(error) {
  stopPolling();
  runState.textContent = "失败";
  errorState.textContent = error.message || "分析任务失败，请检查 .env 配置和后端日志。";
  setView("error");
  form.querySelector(".primary").disabled = false;
}

function setKellyView(view) {
  kellyEmpty.classList.toggle("hidden", view !== "empty");
  kellyResult.classList.toggle("hidden", view !== "result");
  kellyError.classList.toggle("hidden", view !== "error");
}

function renderKellyResult(data) {
  recommendedAmount.textContent = formatCurrency(data.recommended_position_amount);
  kellyVerdict.textContent = data.verdict || "已完成";
  riskCapital.textContent = formatCurrency(data.risk_capital);
  maxLoss.textContent = formatCurrency(data.max_loss_amount);
  positionUnits.textContent = `${formatNumber(Math.floor(data.units), 0)} 股`;
  exposurePct.textContent = formatPercent(data.account_exposure_pct);
  rewardRisk.textContent = `${formatNumber(data.reward_risk_ratio, 2)} : 1`;
  appliedKelly.textContent = formatPercent(data.applied_kelly_fraction);
  stopLossPct.textContent = formatPercent(data.stop_loss_pct);
  takeProfitPct.textContent = formatPercent(data.take_profit_pct);
  tradeDirection.textContent = data.direction === "short" ? "做空" : "做多";
  kellyNotes.innerHTML = (data.notes && data.notes.length ? data.notes : ["该结果基于你输入的主观胜率和价格结构，仅用于仓位测算。"])
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");
  kellyState.textContent = "已完成";
  setKellyView("result");
}

function collectKellyPayload() {
  const formData = new FormData(kellyForm);
  return {
    available_cash: Number(formData.get("available_cash")),
    win_probability: Number(formData.get("win_probability")),
    current_price: Number(formData.get("current_price")),
    take_profit_price: Number(formData.get("take_profit_price")),
    stop_loss_price: Number(formData.get("stop_loss_price")),
    kelly_multiplier: Number(formData.get("kelly_multiplier"))
  };
}

function updateActiveNav() {
  const knownPages = new Set(Array.from(pageViews).map((page) => `#${page.id}`));
  const hash = knownPages.has(window.location.hash) ? window.location.hash : "#dashboard";

  navLinks.forEach((link) => {
    const isActive = link.getAttribute("href") === hash;
    link.classList.toggle("active", isActive);
    link.classList.toggle("muted", !isActive);
  });

  pageViews.forEach((page) => {
    page.classList.toggle("active-page", `#${page.id}` === hash);
  });

  if (window.location.hash !== hash) {
    history.replaceState(null, "", hash);
  }

  if (hash === "#events" && !eventsGrid.dataset.loaded) {
    loadEventFocus(currentEventMarket).catch(handleEventError);
  }
  if (hash === "#dashboard" && !dashboardLoaded) {
    loadDashboard().catch(handleDashboardError);
  }
  if (hash === "#settings" && !systemStatusCards.dataset.loaded) {
    loadSystemStatus().catch(() => {
      systemStatusCards.innerHTML = `<p class="status-error">系统状态读取失败。</p>`;
    });
    loadDataSourceStatus().catch(handleDataSourceError);
  }
  if (hash === "#portfolio" && !portfolioLoaded) {
    loadPortfolio().catch(handlePortfolioError);
  }
}

function scoreLabel(key) {
  return {
    trend: "趋势",
    momentum: "动量",
    quality: "质量",
    value: "估值",
    liquidity: "流动性",
    risk: "风险"
  }[key] || key;
}

function renderRecommendations(items) {
  recommendationList.innerHTML = items
    .map((item) => `
      <button class="recommendation-card" type="button" data-signal-id="${escapeHtml(item.signal_id)}">
        <span class="recommendation-rank">${item.rank}</span>
        <span class="recommendation-identity">
          <strong>${escapeHtml(item.name)}</strong>
          <small>${escapeHtml(item.symbol)} · ${escapeHtml(item.industry || "行业待补充")}</small>
        </span>
        <span class="recommendation-score">
          <strong>${formatNumber(item.final_score, 1)}</strong>
          <small>${escapeHtml(item.side)}</small>
        </span>
        <span class="recommendation-change ${Number(item.change_pct) >= 0 ? "positive" : "negative"}">${formatSignedPercent(item.change_pct)}</span>
      </button>
    `)
    .join("");

  recommendationList.querySelectorAll(".recommendation-card").forEach((button) => {
    button.addEventListener("click", () => loadRecommendationDetail(button.dataset.signalId));
  });
}

function renderWatchlist(items) {
  if (!items.length) {
    watchlistItems.innerHTML = `<p class="compact-empty">暂无自选股。</p>`;
    return;
  }
  watchlistItems.innerHTML = items
    .map((item) => `
      <div class="watchlist-row">
        <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.symbol)}</small></div>
        <button type="button" class="watchlist-remove" data-symbol="${escapeHtml(item.symbol)}">移除</button>
      </div>
    `)
    .join("");
  watchlistItems.querySelectorAll(".watchlist-remove").forEach((button) => {
    button.addEventListener("click", async () => {
      const response = await fetch(`/api/watchlist/${encodeURIComponent(button.dataset.symbol)}`, { method: "DELETE" });
      if (response.ok) renderWatchlist(await response.json());
    });
  });
}

function renderReports(items) {
  dashboardReports.innerHTML = items
    .map((item) => `
      <article class="dashboard-report">
        <span>${item.report_type === "pre_market" ? "盘前" : "盘后"}</span>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.summary)}</p>
      </article>
    `)
    .join("");
}

function renderPriceChart(bars, container = priceChart) {
  if (!bars.length) {
    container.innerHTML = "<p>暂无价格数据。</p>";
    return;
  }
  const width = 900;
  const height = 250;
  const padding = 22;
  const closes = bars.map((bar) => Number(bar.close));
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const points = closes
    .map((close, index) => {
      const x = padding + (index / Math.max(1, closes.length - 1)) * (width - padding * 2);
      const y = height - padding - ((close - min) / range) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  container.innerHTML = `
    <div class="chart-head"><strong>近 ${bars.length} 个交易日趋势</strong><span>${bars[0].date} 至 ${bars.at(-1).date}</span></div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="收盘价趋势">
      <defs><linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b86f3c" stop-opacity=".32"/><stop offset="1" stop-color="#b86f3c" stop-opacity="0"/></linearGradient></defs>
      <polygon points="${padding},${height - padding} ${points} ${width - padding},${height - padding}" fill="url(#chartFill)"></polygon>
      <polyline points="${points}" fill="none" stroke="#b86f3c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
    </svg>
    <div class="chart-foot"><span>最低 ${formatNumber(min, 2)}</span><strong>最新 ${formatNumber(closes.at(-1), 2)}</strong><span>最高 ${formatNumber(max, 2)}</span></div>
  `;
}

function renderTop20(items) {
  top20List.innerHTML = items
    .map((item) => `
      <div class="top20-row" data-symbol="${escapeHtml(item.symbol)}">
        <span class="top20-rank">${item.rank}</span>
        <div class="top20-identity">
          <strong>${escapeHtml(item.name)}</strong>
          <small>${escapeHtml(item.symbol)} · ${escapeHtml(item.industry || "未分类")}</small>
        </div>
        <div class="top20-price">
          <strong>${formatNumber(item.reference_price, 2)}</strong>
          <small class="${Number(item.change_pct) >= 0 ? "positive" : "negative"}">${formatSignedPercent(item.change_pct)}</small>
        </div>
        <div class="top20-score"><strong>${formatNumber(item.final_score, 1)}</strong><small>综合分</small></div>
        <div class="top20-actions">
          <button class="ghost top20-detail" type="button">详情</button>
          <button class="ghost top20-add" type="button">+ 自选</button>
        </div>
      </div>
    `)
    .join("");
  top20List.querySelectorAll(".top20-detail").forEach((button) => {
    button.addEventListener("click", () => loadTrackingDetail(button.closest(".top20-row").dataset.symbol));
  });
  top20List.querySelectorAll(".top20-add").forEach((button) => {
    button.addEventListener("click", () => addTrackedSymbol(button.closest(".top20-row").dataset.symbol));
  });
}

function renderTrackedStocks(items) {
  trackedCount.textContent = `${items.length} 只`;
  if (!items.length) {
    trackedStocks.innerHTML = `<p class="compact-empty">暂无自选股，请从 Top20 或搜索结果中添加。</p>`;
    return;
  }
  trackedStocks.innerHTML = items
    .map((item) => {
      const tracking = item.tracking || {};
      return `
        <article class="tracked-card" data-symbol="${escapeHtml(item.symbol)}">
          <div class="tracked-card-head">
            <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.symbol)} · ${escapeHtml(item.industry || "未分类")}</small></div>
            <span class="tracking-status">${escapeHtml(tracking.tracking_status || "等待数据")}</span>
          </div>
          <div class="tracked-quote">
            <strong>${item.reference_price == null ? "--" : formatNumber(item.reference_price, 2)}</strong>
            <span class="${Number(item.change_pct) >= 0 ? "positive" : "negative"}">${item.change_pct == null ? "--" : formatSignedPercent(item.change_pct)}</span>
          </div>
          <div class="tracked-mini-metrics">
            <span>排名 <strong>${item.rank || "--"}</strong></span>
            <span>评分 <strong>${item.final_score == null ? "--" : formatNumber(item.final_score, 1)}</strong></span>
            <span>区间收益 <strong>${tracking.period_return_pct == null ? "--" : formatSignedPercent(tracking.period_return_pct)}</strong></span>
            <span>MA20 偏离 <strong>${tracking.price_vs_ma20_pct == null ? "--" : formatSignedPercent(tracking.price_vs_ma20_pct)}</strong></span>
          </div>
          <div class="tracked-card-actions">
            <button class="ghost tracked-detail" type="button">查看详情</button>
            <button class="watchlist-remove tracked-remove" type="button">移除</button>
          </div>
        </article>
      `;
    })
    .join("");
  trackedStocks.querySelectorAll(".tracked-detail").forEach((button) => {
    button.addEventListener("click", () => loadTrackingDetail(button.closest(".tracked-card").dataset.symbol));
  });
  trackedStocks.querySelectorAll(".tracked-remove").forEach((button) => {
    button.addEventListener("click", () => removeTrackedSymbol(button.closest(".tracked-card").dataset.symbol));
  });
}

async function addTrackedSymbol(symbol) {
  const response = await fetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol })
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "添加自选失败");
  renderTrackedStocks(data);
  renderWatchlist(data);
  await loadTrackingDetail(symbol);
}

async function removeTrackedSymbol(symbol) {
  const response = await fetch(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "移除自选失败");
  renderTrackedStocks(data);
  renderWatchlist(data);
  if (currentTrackingSymbol === symbol) {
    currentTrackingSymbol = null;
    trackingDetail.classList.add("hidden");
  }
}

async function loadTrackingDetail(symbol) {
  const [snapshotResponse, barsResponse] = await Promise.all([
    fetch(`/api/stocks/${encodeURIComponent(symbol)}`),
    fetch(`/api/stocks/${encodeURIComponent(symbol)}/bars?days=90`)
  ]);
  const item = await snapshotResponse.json();
  if (!snapshotResponse.ok) throw new Error(item.detail || "股票详情读取失败");
  const bars = await barsResponse.json();
  currentTrackingSymbol = item.symbol;
  currentTrackingInWatchlist = Boolean(item.in_watchlist);
  const tracking = item.tracking || {};
  trackingDetailSymbol.textContent = `${item.symbol} · ${item.industry || "未分类"} · ${item.as_of_date || ""}`;
  trackingDetailName.textContent = `${item.name} · ${tracking.tracking_status || "追踪中"}`;
  trackingDetailSummary.textContent = item.summary || "持续跟踪价格趋势、模型排名和因子变化。";
  const metrics = [
    ["当前价", item.reference_price == null ? "--" : formatNumber(item.reference_price, 2)],
    ["当日涨跌", item.change_pct == null ? "--" : formatSignedPercent(item.change_pct)],
    ["模型排名", item.rank || "--"],
    ["综合评分", item.final_score == null ? "--" : formatNumber(item.final_score, 1)],
    ["区间收益", tracking.period_return_pct == null ? "--" : formatSignedPercent(tracking.period_return_pct)],
    ["MA20", tracking.ma20 == null ? "--" : formatNumber(tracking.ma20, 2)],
    ["MA20 偏离", tracking.price_vs_ma20_pct == null ? "--" : formatSignedPercent(tracking.price_vs_ma20_pct)],
    ["区间高 / 低", tracking.period_high == null ? "--" : `${formatNumber(tracking.period_high, 2)} / ${formatNumber(tracking.period_low, 2)}`]
  ];
  trackingMetrics.innerHTML = metrics
    .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
  trackingFactors.innerHTML = Object.entries(item.scores || {})
    .map(([key, value]) => `<div class="tracking-factor"><span>${scoreLabel(key)}</span><strong>${formatNumber(value, 0)}</strong><i style="width:${Math.max(0, Math.min(100, Number(value)))}%"></i></div>`)
    .join("");
  if (barsResponse.ok) renderPriceChart(bars.bars || [], trackingChart);
  trackingRemoveBtn.textContent = item.in_watchlist ? "移出自选" : "加入自选";
  trackingDetail.classList.remove("hidden");
  trackingDetail.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadPortfolio() {
  top20State.textContent = "读取中";
  const [rankingResponse, watchlistResponse] = await Promise.all([
    fetch("/api/recommendations/today?limit=20"),
    fetch("/api/watchlist")
  ]);
  const ranking = await rankingResponse.json();
  if (!rankingResponse.ok) throw new Error(ranking.detail || "Top20 读取失败");
  renderTop20(ranking.items || []);
  top20State.textContent = `${ranking.items.length} 只 · ${ranking.as_of_date}`;
  if (watchlistResponse.ok) renderTrackedStocks(await watchlistResponse.json());
  portfolioLoaded = true;
}

function handlePortfolioError(error) {
  top20State.textContent = "失败";
  top20List.innerHTML = `<p class="status-error">${escapeHtml(error.message || "选股池读取失败")}</p>`;
}

async function loadRecommendationDetail(signalId) {
  const response = await fetch(`/api/recommendations/${encodeURIComponent(signalId)}`);
  const item = await response.json();
  if (!response.ok) throw new Error(item.detail || "推荐详情读取失败");
  currentRecommendation = item;
  detailSymbol.textContent = `${item.symbol} · ${item.industry || "行业待补充"} · ${item.as_of_date}`;
  detailName.textContent = `${item.name} · ${item.side}`;
  detailSummary.textContent = item.summary;
  detailMetrics.innerHTML = Object.entries(item.scores || {})
    .map(([key, value]) => `<div><span>${scoreLabel(key)}</span><strong>${formatNumber(value, 0)}</strong><i style="width:${Math.max(0, Math.min(100, Number(value)))}%"></i></div>`)
    .join("");
  detailReasons.innerHTML = (item.positive_reasons || []).map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  detailRisks.innerHTML = (item.risk_reasons || []).map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  detailInvalidations.innerHTML = (item.invalidation_conditions || []).map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  notificationResult.textContent = "";
  recommendationDetail.classList.remove("hidden");
  const barsResponse = await fetch(`/api/stocks/${encodeURIComponent(item.symbol)}/bars?days=90`);
  const bars = await barsResponse.json();
  if (barsResponse.ok) renderPriceChart(bars.bars || []);
  recommendationDetail.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadDashboard() {
  recommendationState.textContent = "读取中";
  const [dashboardResponse, watchlistResponse] = await Promise.all([
    fetch("/api/dashboard"),
    fetch("/api/watchlist")
  ]);
  const data = await dashboardResponse.json();
  if (!dashboardResponse.ok) throw new Error(data.detail || "首页数据读取失败");
  const recommendations = data.recommendations;
  dashboardMode.textContent = recommendations.data_mode === "tushare_direct"
    ? "Tushare 直连"
    : recommendations.data_mode === "live"
      ? "数据库结果"
      : "Demo 快照";
  dashboardDate.textContent = recommendations.as_of_date;
  dashboardStrategy.textContent = recommendations.strategy_version;
  recommendationState.textContent = `${recommendations.items.length} 只候选`;
  renderRecommendations(recommendations.items || []);
  renderReports(data.latest_reports || []);
  if (watchlistResponse.ok) renderWatchlist(await watchlistResponse.json());
  dashboardLoaded = true;
}

function handleDashboardError(error) {
  recommendationState.textContent = "失败";
  recommendationList.innerHTML = `<p class="status-error">${escapeHtml(error.message || "首页数据读取失败")}</p>`;
}

async function loadSystemStatus() {
  const response = await fetch("/api/system/status");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "系统状态读取失败");
  const cards = [
    ["数据模式", data.data_mode],
    ["数据日期", data.as_of_date],
    ["策略版本", data.strategy_version],
    ["AI 工作流", data.ai_workflow],
    ["消息通道", data.notification_channel]
  ];
  systemStatusCards.innerHTML = cards
    .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
  systemStatusCards.dataset.loaded = "true";
}

function renderDataSourceStatus(data) {
  dataSourceState.textContent = data.configured ? "已配置" : "未配置";
  dataSourceMeta.innerHTML = `
    <div><span>供应商</span><strong>Tushare Pro</strong></div>
    <div><span>Token</span><strong>${data.configured ? escapeHtml(data.token_hint) : "未填写"}</strong></div>
    <div><span>数据模式</span><strong>${escapeHtml(data.data_mode)}</strong></div>
    <div><span>样本池</span><strong>${formatNumber(data.universe_size, 0)} 只</strong></div>
    <div><span>数据日期</span><strong>${escapeHtml(data.as_of_date || "尚未刷新")}</strong></div>
    <div><span>缓存股票</span><strong>${formatNumber(data.item_count, 0)} 只</strong></div>
  `;
  if (data.last_error) {
    dataSourceMessage.textContent = `上次刷新失败：${data.last_error}`;
  }
}

async function loadDataSourceStatus() {
  const response = await fetch("/api/data-source");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "数据源状态读取失败");
  renderDataSourceStatus(data);
}

function handleDataSourceError(error) {
  dataSourceState.textContent = "失败";
  dataSourceMessage.textContent = error.message || "数据源操作失败";
}

async function runDataSourceAction(url, pendingText) {
  dataSourceState.textContent = pendingText;
  dataSourceMessage.textContent = "";
  const response = await fetch(url, { method: "POST" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "数据源操作失败");
  return data;
}

function priorityClass(priority) {
  if (priority === "高") return "high";
  if (priority === "低") return "low";
  return "medium";
}

function eventDirectionClass(direction) {
  if (direction === "利多") return "bullish";
  if (direction === "利空") return "bearish";
  if (direction === "分化") return "divergent";
  return "neutral";
}

function filteredEventCards(cards) {
  if (currentEventFilter === "high") return cards.filter((card) => card.priority === "高");
  if (currentEventFilter === "bullish") return cards.filter((card) => card.impact_direction === "利多");
  if (currentEventFilter === "bearish") return cards.filter((card) => card.impact_direction === "利空");
  return cards;
}

function renderEventFocus(data) {
  currentEventPayload = data;
  eventsGrid.dataset.loaded = "true";
  eventsState.textContent = data.status === "ready" ? "已更新" : "降级";
  eventsSummaryTitle.textContent = data.summary || `${data.market_label}事件聚焦`;
  eventsMeta.textContent = `${data.market_label} · 来源 ${data.source_count || 0} 条 · ${data.generated_at || ""} · ${data.next_refresh_hint || ""}`;
  eventsError.classList.toggle("hidden", !data.error);
  eventsError.textContent = data.error ? `提示：${data.error}` : "";
  eventsEmpty.classList.toggle("hidden", Boolean(data.cards && data.cards.length));
  const overview = data.overview || {};
  eventsOverview.innerHTML = `
    <div><span>高优先级</span><strong>${formatNumber(overview.high_priority_count || 0, 0)}</strong></div>
    <div><span>利多事件</span><strong>${formatNumber(overview.bullish_count || 0, 0)}</strong></div>
    <div><span>利空事件</span><strong>${formatNumber(overview.bearish_count || 0, 0)}</strong></div>
    <div><span>覆盖类别</span><strong>${escapeHtml((overview.categories || []).join(" / ") || "待分类")}</strong></div>
  `;

  const cards = filteredEventCards(data.cards || []);
  eventsEmpty.classList.toggle("hidden", Boolean(cards.length));
  eventsEmpty.querySelector("p").textContent = cards.length
    ? ""
    : "当前筛选条件下暂无事件，请切换筛选或刷新数据。";
  eventsGrid.innerHTML = cards
    .map((card) => {
      const watches = (card.watch_points || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      const link = card.url
        ? `<a class="event-link" href="${escapeHtml(card.url)}" target="_blank" rel="noreferrer">查看来源</a>`
        : "";
      const assets = (card.affected_assets || [])
        .map((item) => `<span>${escapeHtml(item)}</span>`)
        .join("");
      return `
        <article class="event-card ${priorityClass(card.priority)} ${eventDirectionClass(card.impact_direction)}">
          <div class="event-card-head">
            <span>${escapeHtml(card.category || "事件")}</span>
            <strong>${escapeHtml(card.priority || "中")}</strong>
          </div>
          <h3>${escapeHtml(card.title)}</h3>
          <p>${escapeHtml(card.why_it_matters || "等待模型补充重要性说明。")}</p>
          <div class="event-impact-row">
            <span class="impact-direction">${escapeHtml(card.impact_direction || "中性")}</span>
            <span>${escapeHtml(card.horizon || "1-3日")}</span>
            <span>置信度 ${formatNumber(Number(card.confidence || 0) * 100, 0)}%</span>
          </div>
          ${assets ? `<div class="event-assets">${assets}</div>` : ""}
          ${watches ? `<ul>${watches}</ul>` : ""}
          <footer>
            <span>${escapeHtml(card.source || card.market || "")} ${escapeHtml(card.published_at || "")}</span>
            ${link}
          </footer>
        </article>
      `;
    })
    .join("");
}

async function loadEventFocus(market, force = false) {
  currentEventMarket = market;
  eventsState.textContent = force ? "刷新中" : "读取中";
  eventsError.classList.add("hidden");
  eventTabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.market === market);
  });

  const response = await fetch(`/api/events/focus?market=${encodeURIComponent(market)}&force=${force ? "true" : "false"}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "事件聚焦读取失败");
  }
  renderEventFocus(data);
}

function handleEventError(error) {
  eventsState.textContent = "失败";
  eventsError.textContent = error.message || "事件聚焦读取失败，请检查 DeepSeek API Key 和新闻源配置。";
  eventsError.classList.remove("hidden");
}

sampleBtn.addEventListener("click", () => {
  queryInput.value = "全面分析贵州茅台 600519.SH，重点关注长期估值、基本面质量、市场预期差、催化剂和主要风险。";
  queryInput.focus();
});

previewLatestBtn.addEventListener("click", async () => {
  stopPolling();
  closeReportModal();
  runState.textContent = "预览中";
  errorState.textContent = "";
  form.querySelector(".primary").disabled = false;

  try {
    const response = await fetch("/api/dev/latest-report");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "暂无可预览的历史报告");
    }

    renderResult(data);
    runState.textContent = "开发预览";
  } catch (error) {
    handleError(error);
  }
});

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(currentReportPlainText || "");
  copyBtn.textContent = "已复制";
  window.setTimeout(() => {
    copyBtn.textContent = "复制";
  }, 1200);
});

modalCopyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(currentReportPlainText || "");
  modalCopyBtn.textContent = "已复制";
  window.setTimeout(() => {
    modalCopyBtn.textContent = "复制";
  }, 1200);
});

expandReportBtn.addEventListener("click", openReportModal);
closeModalBtn.addEventListener("click", closeReportModal);
modalBackdrop.addEventListener("click", closeReportModal);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !reportModal.classList.contains("hidden")) {
    closeReportModal();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  stopPolling();
  form.querySelector(".primary").disabled = true;
  runState.textContent = "排队中";
  errorState.textContent = "";
  progressList.innerHTML = "";
  activityStream.innerHTML = "";
  reportText.innerHTML = "";
  modalReportContent.innerHTML = "";
  closeReportModal();
  progressBar.style.width = "0%";
  progressPercent.textContent = "0/12";
  loadingText.textContent = "任务正在提交...";
  setView("loading");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        profile: selectedValue("profile"),
        collection_mode: selectedValue("collectionMode")
      })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.message || "分析任务创建失败");
    }

    await pollTask(data.task_id);
  } catch (error) {
    handleError(error);
  }
});

kellySampleBtn.addEventListener("click", () => {
  kellyForm.available_cash.value = "100000";
  kellyForm.win_probability.value = "55";
  kellyForm.current_price.value = "100";
  kellyForm.take_profit_price.value = "116";
  kellyForm.stop_loss_price.value = "94";
  kellyForm.kelly_multiplier.value = "0.5";
});

kellyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  kellyState.textContent = "计算中";
  kellyError.textContent = "";
  kellyForm.querySelector(".primary").disabled = true;

  try {
    const response = await fetch("/api/position/kelly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectKellyPayload())
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "仓位计算失败");
    }
    renderKellyResult(data);
  } catch (error) {
    kellyState.textContent = "失败";
    kellyError.textContent = error.message || "仓位计算失败，请检查输入参数。";
    setKellyView("error");
  } finally {
    kellyForm.querySelector(".primary").disabled = false;
  }
});

eventTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    loadEventFocus(tab.dataset.market || "a_share").catch(handleEventError);
  });
});

eventFilters.forEach((button) => {
  button.addEventListener("click", () => {
    currentEventFilter = button.dataset.filter || "all";
    eventFilters.forEach((item) => item.classList.toggle("active", item === button));
    if (currentEventPayload) renderEventFocus(currentEventPayload);
  });
});

refreshEventsBtn.addEventListener("click", () => {
  loadEventFocus(currentEventMarket, true).catch(handleEventError);
});

detailWatchBtn.addEventListener("click", async () => {
  if (!currentRecommendation) return;
  const response = await fetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol: currentRecommendation.symbol })
  });
  const data = await response.json();
  if (!response.ok) {
    notificationResult.textContent = data.detail || "加入自选失败";
    return;
  }
  renderWatchlist(data);
  detailWatchBtn.textContent = "已加入自选";
});

detailNotifyBtn.addEventListener("click", async () => {
  if (!currentRecommendation) return;
  detailNotifyBtn.disabled = true;
  notificationResult.textContent = "正在发送测试提醒...";
  try {
    const response = await fetch("/api/demo/notifications/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: currentRecommendation.symbol })
    });
    const data = await response.json();
    notificationResult.textContent = data.status === "sent"
      ? "企业微信提醒已发送。"
      : data.status === "simulated"
        ? `模拟提醒成功：${data.content}`
        : `提醒发送失败：${data.error || "未知错误"}`;
  } finally {
    detailNotifyBtn.disabled = false;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  chatMessages.insertAdjacentHTML("beforeend", `<div class="chat-message user">${escapeHtml(message)}</div>`);
  chatInput.value = "";
  chatMode.textContent = "思考中";
  chatForm.querySelector("button").disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, symbol: currentRecommendation?.symbol || null })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "问答请求失败");
    const citations = (data.citations || [])
      .map((item) => `<span>${escapeHtml(item.title)} · ${escapeHtml(item.source)}</span>`)
      .join("");
    chatMessages.insertAdjacentHTML(
      "beforeend",
      `<div class="chat-message assistant">${escapeHtml(data.answer)}${citations ? `<div class="chat-citations">${citations}</div>` : ""}</div>`
    );
    chatMode.textContent = data.mode === "deepseek" ? "DeepSeek" : "规则问答";
  } catch (error) {
    chatMessages.insertAdjacentHTML("beforeend", `<div class="chat-message assistant error-message">${escapeHtml(error.message)}</div>`);
    chatMode.textContent = "失败";
  } finally {
    chatForm.querySelector("button").disabled = false;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});

testTushareBtn.addEventListener("click", async () => {
  try {
    const data = await runDataSourceAction("/api/data-source/test", "测试中");
    dataSourceMessage.textContent = data.message;
    await loadDataSourceStatus();
  } catch (error) {
    handleDataSourceError(error);
  }
});

refreshTushareBtn.addEventListener("click", async () => {
  refreshTushareBtn.disabled = true;
  try {
    const data = await runDataSourceAction("/api/data-source/refresh", "抓取中");
    renderDataSourceStatus(data);
    dataSourceMessage.textContent = `刷新完成：${data.as_of_date}，生成 ${data.item_count} 只推荐候选。`;
    dashboardLoaded = false;
    portfolioLoaded = false;
    await loadDashboard();
  } catch (error) {
    handleDataSourceError(error);
  } finally {
    refreshTushareBtn.disabled = false;
  }
});

watchSearchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = watchSearchInput.value.trim();
  if (!query) return;
  watchSearchResults.innerHTML = `<p class="compact-empty">搜索中...</p>`;
  try {
    const response = await fetch(`/api/stocks/search?q=${encodeURIComponent(query)}`);
    const items = await response.json();
    if (!response.ok) throw new Error(items.detail || "搜索失败");
    if (!items.length) {
      watchSearchResults.innerHTML = `<p class="compact-empty">未找到匹配股票，请输入完整代码或名称。</p>`;
      return;
    }
    watchSearchResults.innerHTML = items
      .map((item) => `
        <div class="watch-search-result" data-symbol="${escapeHtml(item.symbol)}">
          <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.symbol)} · ${escapeHtml(item.industry)}</small></div>
          <div class="watch-search-quote"><strong>${formatNumber(item.reference_price, 2)}</strong><small class="${Number(item.change_pct) >= 0 ? "positive" : "negative"}">${formatSignedPercent(item.change_pct)}</small></div>
          <button class="ghost search-detail" type="button">详情</button>
          <button class="ghost search-add" type="button" ${item.in_watchlist ? "disabled" : ""}>${item.in_watchlist ? "已添加" : "+ 自选"}</button>
        </div>
      `)
      .join("");
    watchSearchResults.querySelectorAll(".search-detail").forEach((button) => {
      button.addEventListener("click", () => loadTrackingDetail(button.closest(".watch-search-result").dataset.symbol));
    });
    watchSearchResults.querySelectorAll(".search-add:not(:disabled)").forEach((button) => {
      button.addEventListener("click", async () => {
        await addTrackedSymbol(button.closest(".watch-search-result").dataset.symbol);
        button.textContent = "已添加";
        button.disabled = true;
      });
    });
  } catch (error) {
    watchSearchResults.innerHTML = `<p class="status-error">${escapeHtml(error.message)}</p>`;
  }
});

trackingRemoveBtn.addEventListener("click", async () => {
  if (!currentTrackingSymbol) return;
  if (currentTrackingInWatchlist) {
    await removeTrackedSymbol(currentTrackingSymbol);
  } else {
    await addTrackedSymbol(currentTrackingSymbol);
  }
});

window.setInterval(() => {
  if (window.location.hash === "#events") {
    loadEventFocus(currentEventMarket).catch(handleEventError);
  }
}, 60_000);

window.addEventListener("hashchange", updateActiveNav);
updateActiveNav();
