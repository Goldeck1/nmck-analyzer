const API_ORIGIN =
  window.location.origin && window.location.origin !== 'null'
    ? window.location.origin
    : 'http://localhost:8000';
const API_URL = `${API_ORIGIN}/api/analyze-product/`;
const STORAGE_KEY = 'nmckPayload';
const RUN_FLAG_KEY = 'nmckShouldFetch';

const defaultPayload = {
  name: 'ноутбук',
  quantity: 15,
  characteristic: 'ноутбук с 8GB RAM'
};

let activeBlobUrl = null;

ready(() => {
  initNmckPage();
  initDonePage();
  initTzPage();
});

function ready(callback) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', callback, { once: true });
  } else {
    callback();
  }
}

function initNmckPage() {
  const form = document.getElementById('product-form');
  if (!form) {
    console.log('Форма product-form не найдена на странице nmck');
    return;
  }
  console.log('Инициализация страницы nmck - форма найдена');

  const nameInput = form.querySelector('[name="name"]');
  const quantityInput = form.querySelector('[name="quantity"]');
  const characteristicInput = form.querySelector('[name="characteristic"]');

  const storedPayload = loadPayload() ?? defaultPayload;

  if (nameInput) nameInput.value = storedPayload.name ?? defaultPayload.name;
  if (quantityInput) quantityInput.value = storedPayload.quantity ?? defaultPayload.quantity;
  if (characteristicInput) characteristicInput.value = storedPayload.characteristic ?? defaultPayload.characteristic;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    console.log('Форма отправлена');

    const payload = {
      name: nameInput.value.trim() || defaultPayload.name,
      quantity: toPositiveInt(quantityInput.value, defaultPayload.quantity),
      characteristic: characteristicInput.value.trim() || defaultPayload.characteristic
    };

    console.log('Payload для сохранения:', payload);
    savePayload(payload);
    sessionStorage.setItem(RUN_FLAG_KEY, 'true');
    console.log('Переход на done.html');
    window.location.href = 'done.html';
  });
}

function initDonePage() {
  const donePage = document.querySelector('.page-done');
  if (!donePage) {
    console.log('Страница done не найдена (селектор .page-done)');
    return;
  }
  console.log('Инициализация страницы done');

  const editableFields = document.querySelectorAll('[data-field]');
  const filesArea = document.querySelector('.generated-files-area');
  const nmckValue = document.querySelector('.nmck-value');

  console.log('Найдены элементы:', {
    editableFields: editableFields.length,
    filesArea: !!filesArea,
    nmckValue: !!nmckValue
  });

  const payload = loadPayload() ?? defaultPayload;
  console.log('Загружен payload:', payload);
  applyPayloadToFields(editableFields, payload);

  // Автоматически отправляем запрос при загрузке страницы
  if (shouldAutofetch()) {
    console.log('Автозапрос включен, отправляем запрос к API');
    const data = collectPayloadFromFields(editableFields);
    console.log('Данные для автозапроса:', data);
    requestNmck(data, { filesArea, nmckValue });
  } else {
    console.log('Автозапрос отключен');
  }
}

function requestNmck(payload, ui) {
  // Если кнопка не передана, все равно выполняем запрос (для автозапроса)
  const initialButtonLabel = ui?.button?.innerHTML;
  if (ui?.button) {
    setButtonState(ui.button, true);
  }
  if (ui?.filesArea) {
    setFilesMessage(ui.filesArea, '      Отправляем запрос на сервер, пожалуйста подождите...');
  }
  if (ui?.nmckValue) {
    setNmckText(ui.nmckValue, 'Запрос выполняется...');
  }

  console.log('Отправка запроса к API:', API_URL, payload);
  return fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(async (response) => {
      if (!response.ok) {
        // Пытаемся получить детали ошибки из JSON ответа
        let errorMessage = `Ошибка ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Если не удалось распарсить JSON, используем стандартное сообщение
          const errorText = await response.text();
          if (errorText) {
            errorMessage = errorText;
          }
        }
        throw new Error(errorMessage);
      }
      return response.blob().then((blob) => ({ blob, response }));
    })
    .then(({ blob, response }) => {
      const filename =
        extractFilename(response.headers.get('Content-Disposition')) ||
        buildFilename(payload);
      const blobUrl = URL.createObjectURL(blob);
      
      // Получаем метаданные из заголовков ответа
      const nmck = response.headers.get('X-NMCK');
      const avgPrice = response.headers.get('X-Avg-Price-Per-Unit');
      const quantity = response.headers.get('X-Quantity');
      
      // Отображаем НМЦК, если он есть
      if (nmck) {
        const nmckFormatted = parseFloat(nmck).toLocaleString('ru-RU', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        });
        setNmckText(ui.nmckValue, `${nmckFormatted} руб.`);
      } else {
        setNmckText(ui.nmckValue, 'Документ сформирован');
      }
      
      renderDownloadBlock(ui.filesArea, filename, blobUrl, blob.size);
    })
    .catch((error) => {
      const errorMessage = `Не удалось получить файл: ${error.message}`;
      setFilesMessage(ui.filesArea, errorMessage, true);
      setNmckText(ui.nmckValue, '—');
    })
    .finally(() => {
      if (ui?.button) {
        setButtonState(ui.button, false, initialButtonLabel);
      }
    });
}

function renderDownloadBlock(container, filename, blobUrl, size) {
  if (!container) {
    return;
  }

  if (activeBlobUrl) {
    URL.revokeObjectURL(activeBlobUrl);
  }
  activeBlobUrl = blobUrl;

  container.innerHTML = '';

  const wrapper = document.createElement('div');
  wrapper.className = 'generated-file';

  const meta = document.createElement('div');
  meta.className = 'file-meta';
  const title = document.createElement('strong');
  title.textContent = filename;
  const sizeNode = document.createElement('span');
  sizeNode.textContent = ` · ${formatSize(size)}`;
  meta.append(title, sizeNode);

  const downloadLink = document.createElement('a');
  downloadLink.className = 'btn-download';
  downloadLink.href = blobUrl;
  downloadLink.download = filename;
  downloadLink.textContent = 'Скачать';

  wrapper.append(meta, downloadLink);
  container.appendChild(wrapper);
}

function setFilesMessage(container, message, isError = false) {
  if (!container) {
    return;
  }

  const paragraph = document.createElement('p');
  paragraph.textContent = message;
  paragraph.style.color = isError ? '#b3261e' : 'inherit';

  container.innerHTML = '';
  container.appendChild(paragraph);
}

function setNmckText(element, text) {
  if (element) {
    element.textContent = text;
  }
}

function applyPayloadToFields(fields, payload) {
  fields.forEach((field) => {
    const key = field.dataset.field;
    if (!key) return;
    const value = payload[key] ?? defaultPayload[key];
    field.textContent =
      key === 'quantity' ? String(value ?? defaultPayload.quantity) : value ?? '';
  });
}

function collectPayloadFromFields(fields) {
  const payload = { ...defaultPayload };

  fields.forEach((field) => {
    const key = field.dataset.field;
    if (!key) return;
    const rawValue = field.textContent.trim();
    if (key === 'quantity') {
      payload.quantity = toPositiveInt(rawValue, defaultPayload.quantity);
    } else if (rawValue) {
      payload[key] = rawValue;
    }
  });

  return payload;
}

function setButtonState(button, isLoading, label) {
  if (!button) {
    return;
  }

  button.disabled = isLoading;
  if (isLoading) {
    button.innerText = 'Формируем...';
  } else if (label) {
    button.innerHTML = label;
  }
}

function savePayload(payload) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    console.warn('Не удалось сохранить payload в sessionStorage');
  }
}

function loadPayload() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function shouldAutofetch() {
  const should = sessionStorage.getItem(RUN_FLAG_KEY) === 'true';
  if (should) {
    sessionStorage.removeItem(RUN_FLAG_KEY);
  }
  return should;
}

function extractFilename(contentDisposition) {
  if (!contentDisposition) {
    return null;
  }

  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(contentDisposition);
  if (!match) {
    return null;
  }

  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

function buildFilename(payload) {
  const cleanName = payload.name.replace(/\s+/g, '_').toLowerCase();
  return `nmck_${cleanName || 'result'}.docx`;
}

function formatSize(bytes) {
  if (!bytes) {
    return '0 Б';
  }
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} КБ`;
  }
  const mb = kb / 1024;
  return `${mb.toFixed(1)} МБ`;
}

function toPositiveInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

// ================================
// === ФУНКЦИИ ДЛЯ СТРАНИЦЫ ТЗ ===
// ================================

const TZ_API_START = `${API_ORIGIN}/api/tz/start`;
const TZ_API_CONTINUE = `${API_ORIGIN}/api/tz/continue`;
const TZ_DIALOG_HISTORY_KEY = 'tzDialogHistory';
const TZ_INITIAL_DATA_KEY = 'tzInitialData';

let tzDialogHistory = [];
let tzInitialData = null;

function initTzPage() {
  const tzPage = document.querySelector('.page-tz');
  if (!tzPage) {
    return;
  }

  const initialForm = document.getElementById('tz-initial-form');
  const dialogContainer = document.getElementById('dialog-container');
  const dialogHistory = document.getElementById('dialog-history');
  const ideasContainer = document.getElementById('ideas-container');
  const tzResultContainer = document.getElementById('tz-result-container');
  const questionResponseContainer = document.getElementById('question-response-container');
  const questionResponseForm = document.getElementById('question-response-form');
  const restartBtn = document.getElementById('restart-btn');

  // Обработчик кнопки "Начать заново"
  if (restartBtn) {
    restartBtn.addEventListener('click', () => {
      resetTzForm();
    });
  }

  // Загружаем историю диалога и начальные данные, если есть
  loadDialogHistory();
  loadInitialData();

  // Если есть история, показываем диалог
  if (tzDialogHistory.length > 0) {
    const initialFormCard = document.getElementById('initial-form');
    if (initialFormCard) {
      initialFormCard.style.display = 'none';
    }
    if (dialogContainer) {
      dialogContainer.style.display = 'flex';
    }
    renderDialogHistory();
  }

  // Обработка начальной формы
  if (initialForm) {
    initialForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(initialForm);
      const name = formData.get('name').trim();
      const characteristics = formData.get('characteristics').trim();

      if (!name || !characteristics) {
        alert('Пожалуйста, заполните все поля');
        return;
      }

      tzInitialData = { name, characteristics };
      saveInitialData();

      // Скрываем форму, показываем диалог
      const initialFormCard = document.getElementById('initial-form');
      const dialogContainerEl = document.getElementById('dialog-container');
      
      if (initialFormCard) {
        initialFormCard.style.display = 'none';
      }
      if (dialogContainerEl) {
        dialogContainerEl.style.display = 'flex';
      }

      // Добавляем сообщение пользователя
      addMessageToHistory('user', `Название: ${name}\nХарактеристики: ${characteristics}`);

      // Показываем индикатор загрузки
      showLoadingIndicator();

      // Отправляем начальный запрос
      try {
        const response = await sendInitialRequest(name, characteristics);
        hideLoadingIndicator();
        displayIdeas(response.ideas);
      } catch (error) {
        hideLoadingIndicator();
        addMessageToHistory('ai', `Ошибка: ${error.message}`);
      }
    });
  }

  // Обработка ответа на вопрос
  if (questionResponseForm) {
    questionResponseForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(questionResponseForm);
      const response = formData.get('response').trim();

      if (!response) {
        alert('Пожалуйста, введите ответ');
        return;
      }

      // Добавляем ответ пользователя в историю
      addMessageToHistory('user', response);
      questionResponseContainer.style.display = 'none';
      questionResponseForm.reset();

      // Показываем индикатор загрузки
      showLoadingIndicator();

      // Отправляем ответ
      try {
        const result = await sendUserResponse(null, response);
        hideLoadingIndicator();
        
        if (result.ideas) {
          // Получили новые варианты
          displayIdeas(result.ideas);
        } else if (result.technical_specification) {
          // Получили финальное ТЗ
          displayTechnicalSpec(result.technical_specification, result.okpd2_codes || []);
        }
      } catch (error) {
        hideLoadingIndicator();
        addMessageToHistory('ai', `Ошибка: ${error.message}`);
      }
    });
  }
}

async function sendInitialRequest(name, characteristics) {
  const response = await fetch(TZ_API_START, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, characteristics })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Ошибка ${response.status}`);
  }

  return await response.json();
}

function displayIdeas(ideas) {
  const ideasContainer = document.getElementById('ideas-container');
  if (!ideasContainer) return;

  ideasContainer.innerHTML = '';

  ideas.forEach((idea) => {
    const button = document.createElement('button');
    button.className = `idea-button ${idea.id === 4 ? 'no-match' : ''}`;
    button.textContent = idea.text;
    button.addEventListener('click', () => handleIdeaSelection(idea.id, idea.text));
    ideasContainer.appendChild(button);
  });
}

async function handleIdeaSelection(ideaId, ideaText) {
  // Скрываем варианты
  document.getElementById('ideas-container').innerHTML = '';

  // Добавляем выбор в историю
  addMessageToHistory('user', ideaText);

  // Показываем индикатор загрузки
  showLoadingIndicator();

  try {
    const result = await sendUserResponse(ideaId, ideaText);
    hideLoadingIndicator();

    if (result.ideas) {
      // Получили новые варианты
      displayIdeas(result.ideas);
    } else if (result.question) {
      // Получили встречный вопрос
      displayQuestion(result.question);
    } else if (result.technical_specification) {
      // Получили финальное ТЗ
      displayTechnicalSpec(result.technical_specification, result.okpd2_codes || []);
    }
  } catch (error) {
    hideLoadingIndicator();
    addMessageToHistory('ai', `Ошибка: ${error.message}`);
  }
}

async function sendUserResponse(ideaId, ideaText) {
  const payload = {
    idea_id: ideaId,
    idea_text: ideaText,
    dialog_history: tzDialogHistory
  };
  
  // Добавляем исходные данные, если они есть
  if (tzInitialData) {
    payload.name = tzInitialData.name;
    payload.characteristics = tzInitialData.characteristics;
  }

  const response = await fetch(TZ_API_CONTINUE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Ошибка ${response.status}`);
  }

  return await response.json();
}

function displayQuestion(question) {
  addMessageToHistory('ai', question);
  document.getElementById('question-response-container').style.display = 'block';
  document.getElementById('question-response-container').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function displayTechnicalSpec(spec, okpd2Codes) {
  const tzResultContainer = document.getElementById('tz-result-container');
  if (!tzResultContainer) return;

  tzResultContainer.innerHTML = '';

  const title = document.createElement('h3');
  title.className = 'tz-result-title';
  title.textContent = 'Техническое задание';

  const content = document.createElement('div');
  content.className = 'tz-result-content';
  content.textContent = spec;

  tzResultContainer.appendChild(title);
  tzResultContainer.appendChild(content);

  // Добавляем OKPD2 коды, если есть
  if (okpd2Codes && okpd2Codes.length > 0) {
    const okpd2Section = document.createElement('div');
    okpd2Section.className = 'okpd2-codes';

    const label = document.createElement('div');
    label.className = 'okpd2-label';
    label.textContent = 'Коды ОКПД2:';

    const list = document.createElement('div');
    list.className = 'okpd2-list';

    okpd2Codes.forEach((code) => {
      const badge = document.createElement('span');
      badge.className = 'okpd2-badge';
      badge.textContent = code;
      list.appendChild(badge);
    });

    okpd2Section.appendChild(label);
    okpd2Section.appendChild(list);
    tzResultContainer.appendChild(okpd2Section);
  }

  // Формируем текст для истории
  const historyText = `Техническое задание:\n\n${spec}${okpd2Codes && okpd2Codes.length > 0 ? `\n\nКоды ОКПД2: ${okpd2Codes.join(', ')}` : ''}`;
  addMessageToHistory('ai', historyText);

  tzResultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addMessageToHistory(role, text) {
  tzDialogHistory.push({ role, text, timestamp: Date.now() });
  saveDialogHistory();
  renderDialogHistory();
}

function renderDialogHistory() {
  const dialogHistory = document.getElementById('dialog-history');
  if (!dialogHistory) return;

  dialogHistory.innerHTML = '';

  tzDialogHistory.forEach((msg) => {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${msg.role}`;

    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = msg.role === 'user' ? 'Вы' : 'ИИ';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = msg.text;

    messageDiv.appendChild(label);
    messageDiv.appendChild(bubble);
    dialogHistory.appendChild(messageDiv);
  });

  dialogHistory.scrollTop = dialogHistory.scrollHeight;
}

function showLoadingIndicator() {
  const dialogHistory = document.getElementById('dialog-history');
  if (!dialogHistory) return;

  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message message-ai';
  loadingDiv.id = 'loading-indicator';

  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = 'ИИ';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble loading-indicator';
  bubble.innerHTML = '<div class="loading-dots"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div>';

  loadingDiv.appendChild(label);
  loadingDiv.appendChild(bubble);
  dialogHistory.appendChild(loadingDiv);
  dialogHistory.scrollTop = dialogHistory.scrollHeight;
}

function hideLoadingIndicator() {
  const loadingIndicator = document.getElementById('loading-indicator');
  if (loadingIndicator) {
    loadingIndicator.remove();
  }
}

function saveDialogHistory() {
  try {
    sessionStorage.setItem(TZ_DIALOG_HISTORY_KEY, JSON.stringify(tzDialogHistory));
  } catch (error) {
    console.warn('Не удалось сохранить историю диалога:', error);
  }
}

function loadDialogHistory() {
  try {
    const stored = sessionStorage.getItem(TZ_DIALOG_HISTORY_KEY);
    if (stored) {
      tzDialogHistory = JSON.parse(stored);
    }
  } catch (error) {
    console.warn('Не удалось загрузить историю диалога:', error);
    tzDialogHistory = [];
  }
}

function saveInitialData() {
  try {
    sessionStorage.setItem(TZ_INITIAL_DATA_KEY, JSON.stringify(tzInitialData));
  } catch (error) {
    console.warn('Не удалось сохранить начальные данные:', error);
  }
}

function loadInitialData() {
  try {
    const stored = sessionStorage.getItem(TZ_INITIAL_DATA_KEY);
    if (stored) {
      tzInitialData = JSON.parse(stored);
    }
  } catch (error) {
    console.warn('Не удалось загрузить начальные данные:', error);
    tzInitialData = null;
  }
}

function resetTzForm() {
  // Очищаем данные
  tzDialogHistory = [];
  tzInitialData = null;
  
  // Очищаем хранилище
  sessionStorage.removeItem(TZ_DIALOG_HISTORY_KEY);
  sessionStorage.removeItem(TZ_INITIAL_DATA_KEY);
  
  // Получаем все необходимые элементы
  const dialogHistory = document.getElementById('dialog-history');
  const ideasContainer = document.getElementById('ideas-container');
  const tzResultContainer = document.getElementById('tz-result-container');
  const questionResponseContainer = document.getElementById('question-response-container');
  const initialForm = document.getElementById('tz-initial-form');
  const initialFormCard = document.getElementById('initial-form');
  const dialogContainer = document.getElementById('dialog-container');
  
  // Очищаем содержимое элементов диалога (но не удаляем сами элементы)
  if (dialogHistory) {
    dialogHistory.innerHTML = '';
  }
  if (ideasContainer) {
    ideasContainer.innerHTML = '';
  }
  if (tzResultContainer) {
    tzResultContainer.innerHTML = '';
  }
  
  // Скрываем контейнер для ответа на вопрос
  if (questionResponseContainer) {
    questionResponseContainer.style.display = 'none';
    const form = document.getElementById('question-response-form');
    if (form) {
      form.reset();
    }
  }
  
  // Скрываем контейнер диалога
  if (dialogContainer) {
    dialogContainer.style.display = 'none';
  }
  
  // Сбрасываем и показываем начальную форму
  if (initialForm) {
    initialForm.reset();
  }
  if (initialFormCard) {
    initialFormCard.style.display = 'block';
  }
  
  // Прокручиваем страницу к начальной форме для лучшего UX
  if (initialFormCard) {
    initialFormCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
