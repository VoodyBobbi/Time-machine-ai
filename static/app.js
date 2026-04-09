const form = document.getElementById("generation-form");
const yearInput = document.getElementById("year-input");
const styleInput = document.getElementById("style-input");
const styleGrid = document.getElementById("style-grid");
const submitButton = document.getElementById("submit-button");

const statusTitle = document.getElementById("status-title");
const statusBadge = document.getElementById("status-badge");
const progressFill = document.getElementById("progress-fill");
const progressValue = document.getElementById("progress-value");
const progressMessage = document.getElementById("progress-message");
const errorBox = document.getElementById("error-box");
const successBox = document.getElementById("success-box");

const resultCard = document.getElementById("result-card");
const resultYear = document.getElementById("result-year");
const resultStyle = document.getElementById("result-style");
const resultDescription = document.getElementById("result-description");
const resultImage = document.getElementById("result-image");
const resultEmpty = document.getElementById("result-empty");

let pollTimer = null;

function formatYearLabel(year) {
  const numericYear = Number(year);
  if (!Number.isFinite(numericYear)) {
    return String(year);
  }
  if (numericYear < 0) {
    return `${Math.abs(numericYear)} до н. э.`;
  }
  return String(numericYear);
}

function setActiveStyleCard(styleKey) {
  for (const card of styleGrid.querySelectorAll(".style-card")) {
    const isActive = card.dataset.styleKey === styleKey;
    card.classList.toggle("is-active", isActive);
    card.setAttribute("aria-pressed", isActive ? "true" : "false");
  }
}

function setProgress(percent, message) {
  progressFill.style.width = `${percent}%`;
  progressValue.textContent = `${percent}%`;
  progressMessage.textContent = message;
}

function clearMessages() {
  errorBox.classList.add("is-hidden");
  errorBox.textContent = "";
  successBox.classList.add("is-hidden");
  successBox.textContent = "";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("is-hidden");
}

function showSuccess(message) {
  successBox.textContent = message;
  successBox.classList.remove("is-hidden");
}

function resetResult() {
  resultCard.classList.add("is-hidden");
  resultEmpty.classList.remove("is-hidden");
  resultYear.textContent = "Одна итоговая картинка";
  resultStyle.textContent = "";
  resultDescription.textContent = "";
  resultImage.removeAttribute("src");
}

function setBusyState(isBusy) {
  submitButton.disabled = isBusy;
  yearInput.disabled = isBusy;
  for (const card of styleGrid.querySelectorAll(".style-card")) {
    card.disabled = isBusy;
  }
}

function renderResult(job) {
  resultEmpty.classList.add("is-hidden");
  resultCard.classList.remove("is-hidden");
  resultYear.textContent = `Год ${formatYearLabel(job.year)}`;
  resultStyle.textContent = `Стиль: ${job.style_label}`;
  resultDescription.textContent = job.description_ru || "";
  if (job.image_url) {
    resultImage.src = `${job.image_url}?v=${encodeURIComponent(job.updated_at || "")}`;
  }
}

function updateStatus(job) {
  setProgress(job.progress || 0, job.message || "Обновление статуса");

  if (job.status === "queued") {
    statusTitle.textContent = "Задача ожидает запуска";
    statusBadge.textContent = "В очереди";
  } else if (job.status === "running") {
    statusTitle.textContent = `Генерация года ${formatYearLabel(job.year)}`;
    statusBadge.textContent = "В процессе";
  } else if (job.status === "completed") {
    statusTitle.textContent = `Результат для ${formatYearLabel(job.year)} готов`;
    statusBadge.textContent = "Готово";
    showSuccess("Готово. Ниже показана итоговая картинка.");
    renderResult(job);
  } else if (job.status === "error") {
    statusTitle.textContent = "Ошибка генерации";
    statusBadge.textContent = "Ошибка";
    showError(job.error || job.message || "Не удалось завершить генерацию.");
  }
}

async function fetchJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error("Не удалось получить статус задачи.");
  }
  return response.json();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function startPolling(jobId) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const job = await fetchJob(jobId);
      updateStatus(job);
      if (job.status === "completed" || job.status === "error") {
        stopPolling();
        setBusyState(false);
      }
    } catch (error) {
      stopPolling();
      setBusyState(false);
      showError(error.message);
    }
  }, 1200);
}

async function createJob(year, style) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ year, style }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Не удалось создать задачу.");
  }
  return payload.job;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessages();
  resetResult();
  stopPolling();
  setBusyState(true);

  const year = yearInput.value.trim();
  const style = styleInput.value;

  statusTitle.textContent = "Запуск генерации";
  statusBadge.textContent = "Старт";
  setProgress(2, "Отправляю запрос на сервер");

  try {
    const job = await createJob(year, style);
    updateStatus(job);
    startPolling(job.id);
  } catch (error) {
    setBusyState(false);
    showError(error.message);
    statusTitle.textContent = "Не удалось запустить задачу";
    statusBadge.textContent = "Ошибка";
  }
});

styleGrid.addEventListener("click", (event) => {
  const card = event.target.closest(".style-card");
  if (!card) {
    return;
  }
  const styleKey = card.dataset.styleKey;
  styleInput.value = styleKey;
  setActiveStyleCard(styleKey);
});

setActiveStyleCard(styleInput.value);
resetResult();
