document.addEventListener('DOMContentLoaded', () => {
    // Dark mode toggle
    const toggle = document.getElementById('dark_mode_toggle');
    if (toggle) {
        toggle.addEventListener('change', () => {
            fetch('/toggle_dark_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            document.body.classList.toggle('dark');
        });
    }

    // Filter transactions
    const input = document.getElementById('search_input');
    const clearButton = document.getElementById('clear_button');
    if (input) {
        function escapeRegExp(string) {
            return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
        function filterByDescription() {
            const entries = document.querySelectorAll('[data-desc]');
            const query = input.value.trim().toLowerCase();
            const txnHeader = document.getElementById('txn_header');
            const noMatchMsg = document.getElementById('no_match_msg');
            let foundMatch = false;
            entries.forEach(entry => {
                const desc = entry.getAttribute('data-desc');
                const textBox = entry.querySelector('.desc');
                if (desc.toLowerCase().includes(query)) {
                    const anyCaseQuery = new RegExp(`(${escapeRegExp(query)})`, 'gi');
                    textBox.innerHTML = desc.replaceAll(
                        anyCaseQuery, `<span class='highlight'>$1</span>`);
                    foundMatch = true;
                    entry.style.display = '';
                } else {
                    entry.style.display = 'none';
                }
            });
            if (foundMatch) {
                noMatchMsg.classList.add('hidden');
                txnHeader.classList.remove('hidden');
            } else {
                noMatchMsg.classList.remove('hidden');
                txnHeader.classList.add('hidden');
            }
        }
        input.addEventListener('input', filterByDescription);
        clearButton.addEventListener('click', () => {
            input.value = '';
            filterByDescription();
            input.focus();
        })
    }

    // Fixing a pyhtml-enhanced bug r.e. random whitespace
    // appearing when displaying multi-line text
    const descriptions = document.querySelectorAll('.desc');
    descriptions.forEach(desc => {
        const cleaned = desc.textContent
            .split('\n')
            .map(line => line.replace(/^ {10}/, ''))
            .map(line => line.replace(/^ {8}/, ''))
            .join('\n');
        desc.textContent = cleaned;
    });
});
