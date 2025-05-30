document.addEventListener('DOMContentLoaded', function () {
    const themeToggle = document.getElementById('themeCheckbox');
    const currentTheme = localStorage.getItem('theme') ? localStorage.getItem('theme') : null;

    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (currentTheme === 'dark') {
            if (themeToggle) themeToggle.checked = true;
        }
    } else {
        // Если тема не сохранена, проверяем системные настройки
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (themeToggle) themeToggle.checked = true;
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    }


    if (themeToggle) {
        themeToggle.addEventListener('change', function (event) {
            if (event.target.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                document.dispatchEvent(new CustomEvent('themeChanged', {detail: {theme: 'dark'}})); // Генерируем событие
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                document.dispatchEvent(new CustomEvent('themeChanged', {detail: {theme: 'light'}})); // Генерируем событие
            }
        });
    }

    const darkThemeMq = window.matchMedia("(prefers-color-scheme: dark)");
    darkThemeMq.addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                if (themeToggle) themeToggle.checked = true;
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                if (themeToggle) themeToggle.checked = false;
            }
        }
    });
});