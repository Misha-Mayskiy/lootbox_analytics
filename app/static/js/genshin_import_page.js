document.addEventListener('DOMContentLoaded', function () {
    const importForm = document.getElementById('importUrlForm');
    const urlInput = document.getElementById('wishHistoryUrl');
    const submitBtn = document.getElementById('submitImportBtn');

    const importResultCard = document.getElementById('importResultCard');
    const resultIconDiv = document.getElementById('importResultIcon');
    const resultMessage = document.getElementById('resultMessage');
    const resultInserted = document.getElementById('resultInserted');
    const resultSkipped = document.getElementById('resultSkipped');
    const resultActions = document.getElementById('resultActions');

    const fetchErrorsContainer = document.getElementById('resultFetchErrorsContainer');
    const fetchErrorsList = document.getElementById('resultFetchErrorsList');
    const processingErrorsContainer = document.getElementById('resultProcessingErrorsContainer');
    const processingErrorsList = document.getElementById('resultProcessingErrorsList');

    const csrfTokenElement = document.getElementById('csrf_token_value_import'); // Если есть
    const csrfToken = csrfTokenElement ? csrfTokenElement.value : null;

    if (importForm && submitBtn) {
        const originalButtonHTML = submitBtn.innerHTML;

        importForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const wishUrl = urlInput.value.trim();
            if (!wishUrl) {
                alert('Пожалуйста, вставьте URL.');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Импорт...';

            importResultCard.style.display = 'block';
            resultIconDiv.innerHTML = ''; // Очищаем иконку
            resultMessage.className = 'font-weight-bold text-center text-info';
            resultMessage.innerText = 'Идет обработка, пожалуйста, подождите...';
            resultInserted.innerText = '-';
            resultSkipped.innerText = '-';
            fetchErrorsContainer.style.display = 'none';
            fetchErrorsList.innerHTML = '';
            processingErrorsContainer.style.display = 'none';
            processingErrorsList.innerHTML = '';
            resultActions.style.display = 'none';

            const headers = {'Content-Type': 'application/json'};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            fetch(window.genshinImportUrl, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({wish_history_url: wishUrl})
            })
                .then(response => response.json().then(data => ({
                    ok: response.ok,
                    status: response.status,
                    body: data
                })))
                .then(dataObj => {
                    resultMessage.innerText = dataObj.body.message || 'Обработка завершена.';
                    resultInserted.innerText = dataObj.body.inserted !== undefined ? dataObj.body.inserted : '-';
                    resultSkipped.innerText = dataObj.body.skipped !== undefined ? dataObj.body.skipped : '-';

                    if (dataObj.ok) {
                        resultMessage.className = 'font-weight-bold text-center text-success';
                        resultIconDiv.innerHTML = '<svg width="48" height="48" viewBox="0 0 16 16" class="bi bi-check-circle-fill text-success" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg>';
                        if (dataObj.body.inserted > 0) { // Показываем кнопку, только если что-то вставлено
                            resultActions.style.display = 'block';
                        }
                    } else {
                        resultMessage.className = 'font-weight-bold text-center text-danger';
                        resultIconDiv.innerHTML = '<svg width="48" height="48" viewBox="0 0 16 16" class="bi bi-x-circle-fill text-danger" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293 5.354 4.646z"/></svg>';
                    }

                    if (dataObj.body.fetch_api_errors && dataObj.body.fetch_api_errors.length > 0) {
                        fetchErrorsContainer.style.display = 'block';
                        dataObj.body.fetch_api_errors.forEach(err => {
                            const li = document.createElement('li');
                            li.textContent = err;
                            fetchErrorsList.appendChild(li);
                        });
                    }
                    if (dataObj.body.processing_db_errors && dataObj.body.processing_db_errors.length > 0) {
                        processingErrorsContainer.style.display = 'block';
                        dataObj.body.processing_db_errors.forEach(err => {
                            const li = document.createElement('li');
                            li.textContent = err;
                            processingErrorsList.appendChild(li);
                        });
                    }
                    if (!dataObj.ok && dataObj.body.inserted === 0 && dataObj.body.skipped === 0) { // Если общая ошибка, а не просто 0 вставлено
                        // Можно дополнительно скрыть детали, если они нерелевантны
                    }
                    urlInput.value = '';
                })
                .catch(error => {
                    resultMessage.innerText = `Произошла ошибка: ${error.message}`;
                    resultMessage.className = 'font-weight-bold text-center text-danger';
                    resultIconDiv.innerHTML = '<svg width="48" height="48" viewBox="0 0 16 16" class="bi bi-exclamation-triangle-fill text-danger" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/></svg>';
                    console.error('Ошибка:', error);
                })
                .finally(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalButtonHTML;
                });
        });
    }
});

function copyCommand() {
    const commandTextElement = document.getElementById('psCommand');
    if (!commandTextElement) {
        console.error("Элемент с ID 'psCommand' не найден.");
        alert('Ошибка: не найден элемент с командой.');
        return;
    }
    const commandText = commandTextElement.innerText; // Берем innerText, т.к. в <pre><code>

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(commandText).then(function () {
        }, function (err) {
            alert('Не удалось скопировать команду автоматически. Пожалуйста, скопируйте вручную.');
            console.error('Ошибка копирования в буфер обмена: ', err);
        });
    } else {
        // Фоллбэк для старых браузеров или если clipboard API недоступен (например, на http)
        const textArea = document.createElement("textarea");
        textArea.value = commandText;
        textArea.style.position = "fixed";  // Убираем из видимой области
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
        } catch (err) {
            alert('Не удалось скопировать команду. Пожалуйста, скопируйте вручную.');
            console.error('Ошибка копирования (fallback): ', err);
        }
        document.body.removeChild(textArea);
    }
}