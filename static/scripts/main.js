document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('transcribe-form');
    const submitBtn = document.getElementById('submit-btn');
    const progressArea = document.getElementById('progress-area');
    const progressBar = document.getElementById('progress-bar');
    const etaLabel = document.getElementById('eta');

    // Overestimated times (seconds) for CPU-only execution
    const ESTIMATES = {
        tiny: 15,
        base: 30,
        small: 60,
        medium: 180,
        large: 600,
    };

    function formatSeconds(s) {
        if (s >= 60) {
            const m = Math.floor(s / 60);
            const sec = Math.round(s % 60);
            return `${m}m ${sec}s`;
        }
        return `${Math.round(s)}s`;
    }

    if (!form) return;

    form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        if (!submitBtn) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Transcribing...';

        // prepare form data
        const fd = new FormData(form);
        const model = fd.get('model_size') || 'small';
        const estimate = ESTIMATES[model] || 60;

        // show progress UI
        if (progressArea) progressArea.style.display = 'block';
        let start = Date.now();
        let elapsed = 0;
        let lastProgress = 0;

        // Animate progress linearly toward 95% by estimated time
        const targetBeforeResponse = 95; // percent
        const interval = 500; // ms
        const timer = setInterval(function () {
            elapsed = (Date.now() - start) / 1000; // seconds
            // linear progress toward targetBeforeResponse
            let pct = Math.min(targetBeforeResponse, (elapsed / estimate) * targetBeforeResponse);
            pct = Math.max(pct, lastProgress); // never go backward
            lastProgress = pct;
            if (progressBar) progressBar.style.width = pct + '%';
            const remaining = Math.max(0, Math.round(estimate - elapsed));
            if (etaLabel) etaLabel.textContent = formatSeconds(remaining);
        }, interval);

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: fd,
                credentials: 'same-origin',
            });

            const text = await resp.text();
            // finalize progress
            clearInterval(timer);
            if (progressBar) progressBar.style.width = '100%';
            if (etaLabel) etaLabel.textContent = '0s';

            // replace the document with server response (result page)
            document.open();
            document.write(text);
            document.close();
        } catch (err) {
            clearInterval(timer);
            alert('Transcription failed: ' + err.message);
            if (progressBar) progressBar.style.width = '0%';
            if (progressArea) progressArea.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Transcribe';
        }
    });
});