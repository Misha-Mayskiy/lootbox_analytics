document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('details.js-details-animate').forEach(details => { // Ищем по новому общему классу
        const summary = details.querySelector('summary');
        if (!summary) return;

        let wrapper = details.querySelector('.details-content-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'details-content-wrapper';
            let sibling = summary.nextElementSibling;
            while (sibling) {
                wrapper.appendChild(sibling);
                sibling = summary.nextElementSibling;
            }
            details.appendChild(wrapper);
        }

        Object.assign(wrapper.style, {
            overflow: 'hidden',
            transition: 'max-height 0.3s ease-out'
        });

        const activeFormName = window.activeFormData ? window.activeFormData.activeForm : null; // Предполагаем, что Flask передает это в window.activeFormData
        const canChangeUsername = window.activeFormData ? window.activeFormData.canChangeUsername === false : false; // Приводим к boolean

        const shouldOpenInitially =
            (details.dataset.formName && details.dataset.formName === activeFormName) ||
            (details.dataset.formName === 'username' && canChangeUsername);

        if (shouldOpenInitially && !details.hasAttribute('open')) {
            details.setAttribute('open', '');
        }

        if (details.hasAttribute('open')) {
            wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
        } else {
            wrapper.style.maxHeight = '0';
        }

        summary.addEventListener('click', e => {
            e.preventDefault(); // Отменяем стандартное поведение <details>

            if (details.hasAttribute('open')) {
                // Закрытие
                wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
                requestAnimationFrame(() => {
                    wrapper.style.maxHeight = '0px';
                });

                // Удаляем 'open' после завершения анимации
                wrapper.addEventListener('transitionend', function handler() {
                    details.removeAttribute('open');
                    wrapper.removeEventListener('transitionend', handler);
                }, { once: true });
            } else {
                // Открытие
                details.setAttribute('open', '');
                wrapper.style.maxHeight = wrapper.scrollHeight + 'px';

                wrapper.addEventListener('transitionend', function handler() {
                    if (details.hasAttribute('open')) {
                        wrapper.style.maxHeight = 'none';
                    }
                    wrapper.removeEventListener('transitionend', handler);
                }, { once: true });
            }
        });
    });
});