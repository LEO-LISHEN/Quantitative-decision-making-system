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
const technicalForm = document.querySelector("#technicalForm");
const technicalImage = document.querySelector("#technicalImage");
const technicalImageName = document.querySelector("#technicalImageName");
const technicalPreviewWrap = document.querySelector("#technicalPreviewWrap");
const technicalQuestion = document.querySelector("#technicalQuestion");
const clearTechnicalBtn = document.querySelector("#clearTechnicalBtn");
const technicalState = document.querySelector("#technicalState");
const technicalChatPanel = document.querySelector(".technical-chat-panel");
const technicalEmpty = document.querySelector("#technicalEmpty");
const technicalChat = document.querySelector("#technicalChat");
const technicalError = document.querySelector("#technicalError");

const TECHNICAL_IMAGE_HELP = "支持 Ctrl+V 粘贴多张截图，也可选择 PNG / JPG / WEBP 文件";

let pollingTimer = null;
let currentReportPlainText = "";
let currentEventMarket = "a_share";
let technicalImages = [];
let technicalMessages = [];

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
  currentReportPlainText = report || "报告为空。";
  const renderedReport = renderMarkdown(currentReportPlainText);
  reportText.innerHTML = renderedReport;
  modalReportContent.innerHTML = renderedReport;
  runState.textContent = "已完成";
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
  const hash = knownPages.has(window.location.hash) ? window.location.hash : "#analysis";

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
}

function priorityClass(priority) {
  if (priority === "高") return "high";
  if (priority === "低") return "low";
  return "medium";
}

function renderEventCard(card) {
  const watches = (card.watch_points || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  const assets = (card.affected_assets || [])
    .map((item) => `<span>${escapeHtml(item)}</span>`)
    .join("");
  const link = card.url
    ? `<a class="event-link" href="${escapeHtml(card.url)}" target="_blank" rel="noreferrer">查看来源</a>`
    : "";

  return `
    <article class="event-card ${priorityClass(card.priority)}">
      <div class="event-card-head">
        <span>${escapeHtml(card.market_impact || card.category || "事件")}</span>
        <strong>${escapeHtml(card.priority || "中")}</strong>
      </div>
      <h3>${escapeHtml(card.title)}</h3>
      <div class="event-meta-row">
        <em>${escapeHtml(card.impact_path || "其他")}</em>
        <em>${escapeHtml(card.time_horizon || "短期")}</em>
      </div>
      <p>${escapeHtml(card.why_it_matters || "等待模型补充重要性说明。")}</p>
      ${assets ? `<div class="event-assets">${assets}</div>` : ""}
      ${watches ? `<ul>${watches}</ul>` : ""}
      <footer>
        <span>${escapeHtml(card.source || card.market || "")} ${escapeHtml(card.published_at || "")}</span>
        ${link}
      </footer>
    </article>
  `;
}

function renderEventFocus(data) {
  eventsGrid.dataset.loaded = "true";
  eventsState.textContent = data.status === "ready" ? "已更新" : "降级";
  eventsSummaryTitle.textContent = data.summary || `${data.market_label}事件聚焦`;
  eventsMeta.textContent = `${data.market_label} · 来源 ${data.source_count || 0} 条 · ${data.generated_at || ""} · ${data.next_refresh_hint || ""}`;
  eventsError.classList.toggle("hidden", !data.error);
  eventsError.textContent = data.error ? `提示：${data.error}` : "";
  const cards = data.cards || [];
  eventsEmpty.classList.toggle("hidden", Boolean(cards.length));

  eventsGrid.innerHTML = cards
    .map((card) => renderEventCard(card))
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

function setTechnicalView(view) {
  technicalEmpty.classList.toggle("hidden", view !== "empty");
  technicalChat.classList.toggle("hidden", view !== "chat");
  technicalError.classList.toggle("hidden", view !== "error");
  syncTechnicalPanelHeight();
}

function syncTechnicalPanelHeight() {
  if (!technicalForm || !technicalChatPanel) return;
  if (window.innerWidth <= 920) {
    technicalChatPanel.style.height = "";
    return;
  }
  technicalChatPanel.style.height = `${technicalForm.offsetHeight}px`;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("截图读取失败，请重新选择图片。"));
    reader.readAsDataURL(file);
  });
}

function renderTechnicalChat() {
  technicalChat.innerHTML = technicalMessages
    .map((message) => {
      const images = (message.images || [])
        .map((image, index) => `<img class="technical-message-image" src="${escapeHtml(image)}" alt="用户上传的技术分析截图 ${index + 1}" />`)
        .join("");
      return `
        <article class="technical-message ${message.role}">
          <span>${message.role === "user" ? "你" : "AI"}</span>
          <div>
            ${images ? `<div class="technical-message-images">${images}</div>` : ""}
            <div class="technical-message-text">${renderMarkdown(message.content)}</div>
          </div>
        </article>
      `;
    })
    .join("");
  syncTechnicalPanelHeight();
  technicalChat.scrollTop = technicalChat.scrollHeight;
}

function resetTechnicalAnalysis() {
  technicalImages = [];
  technicalMessages = [];
  technicalForm.reset();
  technicalImageName.textContent = TECHNICAL_IMAGE_HELP;
  renderTechnicalPreviews();
  technicalError.textContent = "";
  technicalState.textContent = "待分析";
  setTechnicalView("empty");
}

function renderTechnicalPreviews() {
  if (!technicalImages.length) {
    technicalPreviewWrap.innerHTML = "";
    technicalPreviewWrap.classList.add("hidden");
    technicalImageName.textContent = TECHNICAL_IMAGE_HELP;
    syncTechnicalPanelHeight();
    return;
  }
  technicalPreviewWrap.classList.remove("hidden");
  technicalImageName.textContent = `${technicalImages.length} 张截图已准备`;
  technicalPreviewWrap.innerHTML = technicalImages
    .map((image) => `
      <article class="technical-preview-card">
        <img src="${escapeHtml(image.dataUrl)}" alt="${escapeHtml(image.name)}" />
        <button class="technical-remove-image" type="button" data-image-id="${escapeHtml(image.id)}" aria-label="删除截图">删除</button>
      </article>
    `)
    .join("");
  syncTechnicalPanelHeight();
}

async function addTechnicalImageFiles(files, sourceLabel = "图片") {
  const selectedFiles = Array.from(files || []);
  if (!selectedFiles.length) return;
  if (technicalImages.length + selectedFiles.length > 6) {
    throw new Error("一次最多支持 6 张截图。");
  }
  const nextImages = [];
  for (const file of selectedFiles) {
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      technicalImage.value = "";
      throw new Error("仅支持 PNG、JPG 或 WEBP 截图。");
    }
    if (file.size > 6 * 1024 * 1024) {
      technicalImage.value = "";
      throw new Error("单张截图大小不能超过 6MB。");
    }
    const dataUrl = await fileToDataUrl(file);
    nextImages.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      name: file.name || sourceLabel,
      size: file.size,
      dataUrl
    });
  }
  technicalImages = [...technicalImages, ...nextImages];
  renderTechnicalPreviews();
  technicalError.textContent = "";
  if (technicalMessages.length === 0) {
    setTechnicalView("empty");
  }
}

async function handleTechnicalImageChange() {
  await addTechnicalImageFiles(technicalImage.files, "选择的截图");
  technicalImage.value = "";
}

async function handleTechnicalPaste(event) {
  const isTechnicalPage = window.location.hash === "#technical";
  const technicalPage = document.querySelector("#technical");
  const isInsideTechnicalModule = technicalPage?.contains(document.activeElement)
    || document.activeElement === document.body;
  if (!isTechnicalPage || !isInsideTechnicalModule) return;

  const imageItems = Array.from(event.clipboardData?.items || [])
    .filter((item) => item.type.startsWith("image/"));
  if (!imageItems.length) return;

  event.preventDefault();
  const files = imageItems.map((item, index) => {
    const file = item.getAsFile();
    if (!file) return null;
    return new File([file], file.name || `pasted-chart-${technicalImages.length + index + 1}.png`, { type: file.type });
  }).filter(Boolean);
  await addTechnicalImageFiles(files, "粘贴的截图");
  technicalState.textContent = "截图已粘贴";
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

technicalImage.addEventListener("change", () => {
  handleTechnicalImageChange().catch((error) => {
    technicalState.textContent = "图片错误";
    technicalError.textContent = error.message || "截图读取失败。";
    setTechnicalView("error");
  });
});

document.addEventListener("paste", (event) => {
  handleTechnicalPaste(event).catch((error) => {
    technicalState.textContent = "粘贴失败";
    technicalError.textContent = error.message || "无法读取剪贴板中的截图。";
    setTechnicalView("error");
  });
});

technicalPreviewWrap.addEventListener("click", (event) => {
  const button = event.target.closest(".technical-remove-image");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  technicalImages = technicalImages.filter((image) => image.id !== button.dataset.imageId);
  renderTechnicalPreviews();
});

clearTechnicalBtn.addEventListener("click", resetTechnicalAnalysis);

technicalForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = technicalQuestion.value.trim();
  if (!question) return;

  technicalState.textContent = "分析中";
  technicalError.textContent = "";
  technicalForm.querySelector(".primary").disabled = true;
  setTechnicalView("chat");

  const userMessage = {
    role: "user",
    content: question,
    images: technicalImages.map((image) => image.dataUrl)
  };
  technicalMessages.push(userMessage);
  renderTechnicalChat();

  try {
    const response = await fetch("/api/technical/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: question,
        image_data_urls: technicalImages.map((image) => image.dataUrl),
        history: technicalMessages
          .slice(0, -1)
          .map((message) => ({ role: message.role, content: message.content }))
      })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "技术分析请求失败");
    }

    technicalMessages.push({ role: "assistant", content: data.analysis || "模型未返回分析内容。" });
    technicalQuestion.value = "";
    technicalState.textContent = "已完成";
    renderTechnicalChat();
  } catch (error) {
    technicalState.textContent = "失败";
    technicalError.textContent = error.message || "技术分析失败，请检查 OPENAI_API_KEY 配置。";
    setTechnicalView("error");
  } finally {
    technicalForm.querySelector(".primary").disabled = false;
  }
});

eventTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    loadEventFocus(tab.dataset.market || "a_share").catch(handleEventError);
  });
});

refreshEventsBtn.addEventListener("click", () => {
  loadEventFocus(currentEventMarket, true).catch(handleEventError);
});

window.setInterval(() => {
  if (window.location.hash === "#events") {
    loadEventFocus(currentEventMarket).catch(handleEventError);
  }
}, 60_000);

window.addEventListener("hashchange", updateActiveNav);
updateActiveNav();
