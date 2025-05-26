document.addEventListener('DOMContentLoaded', () => {
    const activeFormName = "{{ active_form | default('none') }}";

    document.querySelectorAll('details.profile-details-form').forEach(details => {
        const summary = details.querySelector('summary');

        let wrapper = details.querySelector('.details-content-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'details-content-wrapper';
            while (summary.nextSibling) wrapper.appendChild(summary.nextSibling);
            details.appendChild(wrapper);
        }

        Object.assign(wrapper.style, {
            overflow: 'hidden',
            transition: 'max-height 0.3s ease'
        });

        const needOpen =
            details.dataset.formName === activeFormName ||
            (details.dataset.formName === 'username' &&
                "{{ not can_change_username }}".toLowerCase() === 'true');

        if (needOpen) details.setAttribute('open', '');

        wrapper.style.maxHeight = details.hasAttribute('open') ? wrapper.scrollHeight + 'px' : '0';

        summary.addEventListener('click', e => {
            e.preventDefault();

            if (details.hasAttribute('open')) {
                wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
                wrapper.offsetHeight;
                wrapper.style.maxHeight = '0px';
                wrapper.addEventListener('transitionend', function handler() {
                    details.removeAttribute('open');
                    wrapper.removeEventListener('transitionend', handler);
                }, {once: true});
            } else {
                details.setAttribute('open', '');
                requestAnimationFrame(() => {
                    wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
                    wrapper.addEventListener('transitionend', function handler() {
                        wrapper.style.maxHeight = 'none';
                        wrapper.removeEventListener('transitionend', handler);
                    }, {once: true});
                });
            }
        });
    });
});