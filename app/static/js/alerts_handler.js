document.addEventListener('DOMContentLoaded', function () {

    const flashMessages = document.querySelectorAll('.flash-messages-container .alert');
    flashMessages.forEach(function (flash) {
        setTimeout(function () {
            // Плавное исчезновение
            flash.style.transition = 'opacity 0.5s ease-out';
            flash.style.opacity = '0';
            setTimeout(function () {
                flash.style.display = 'none';
            }, 500);
        }, 4000);
    });

    const closeAlertButtons = document.querySelectorAll('.alert .close-alert, .alert [data-dismiss="alert"]'); // Ищем оба варианта
    closeAlertButtons.forEach(button => {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const alertNode = this.closest('.alert');
            if (alertNode) {
                alertNode.classList.add('fade-out');
                setTimeout(() => {
                    alertNode.style.display = 'none';
                    alertNode.classList.remove('fade-out');
                }, 500);
            }
        });
    });

});