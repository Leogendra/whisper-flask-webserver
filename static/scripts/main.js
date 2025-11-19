document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('transcribe-form');
    const submitBtn = document.getElementById('submit-btn');
    const progressArea = document.getElementById('progress-area');
    const progressBar = document.getElementById('progress-bar');
    const etaLabel = document.getElementById('eta');

    const DEFAULT_ASSUMED_DURATION = 30;
    const DEFAULT_FACTOR = 1.0;
    const SPEED_FACTORS = {
        tiny: 0.2,
        base: 0.4,
        small: 0.6,
        medium: 1.5,
        large: 2.5,
    };

    function formatSeconds(s) {
        if (s >= 60) {
            const m = Math.floor(s / 60);
            const sec = Math.round(s % 60);
            return `${m}m ${sec}s`;
        }
        return `${Math.round(s)}s`;
    }

    if (!form) { return; }

    const fileInput = form.querySelector('input[type="file"][name="audio_file"]') || form.querySelector('input[type="file"]');

    if (fileInput) {
        fileInput.addEventListener('change', function (ev) {
            const f = fileInput.files && fileInput.files[0];
            if (!f) {
                form.dataset.audioDuration = '';
                if (etaLabel) etaLabel.textContent = '';
                return;
            }

            const url = URL.createObjectURL(f);
            const a = new Audio();
            a.preload = 'metadata';
            a.src = url;
            a.addEventListener('loadedmetadata', function () {
                const dur = a.duration || 0;
                form.dataset.audioDuration = String(dur);

                const modelSelect = form.querySelector('select[name="model_size"]');
                const model = (modelSelect && modelSelect.value) || 'small';
                const factor = SPEED_FACTORS[model] || DEFAULT_FACTOR;
                const estimate = dur > 0
                    ? Math.max(1, Math.round(dur * factor))
                    : Math.max(1, Math.round(DEFAULT_ASSUMED_DURATION * factor));
                if (etaLabel) etaLabel.textContent = `Duration: ${formatSeconds(dur)} • Est: ${formatSeconds(estimate)}`;

                URL.revokeObjectURL(url);
            });

            a.addEventListener('error', function () {
                form.dataset.audioDuration = '';
                if (etaLabel) etaLabel.textContent = '';
                URL.revokeObjectURL(url);
            });
        });
    }

    form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        if (!submitBtn) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Transcribing...';

        const fd = new FormData(form);
        const model = fd.get('model_size') || 'small';
        const audioDuration = parseFloat(form.dataset.audioDuration) || 0;
        if (audioDuration > 0) fd.set('audio_duration', String(audioDuration));
        const factor = SPEED_FACTORS[model] || DEFAULT_FACTOR;
        const estimate = audioDuration > 0
            ? Math.max(1, audioDuration * factor)
            : Math.max(1, DEFAULT_ASSUMED_DURATION * factor);

        if (progressArea) progressArea.style.display = 'block';
        let start = Date.now();
        let elapsed = 0;
        let lastProgress = 0;

        // Animate progress linearly toward 95% by estimated time
        const targetBeforeResponse = 95;
        const interval = 500;
        const timer = setInterval(function () {
            elapsed = (Date.now() - start) / 1000;
            let pct = Math.min(targetBeforeResponse, (elapsed / estimate) * targetBeforeResponse);
            pct = Math.max(pct, lastProgress);
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
            clearInterval(timer);
            if (progressBar) progressBar.style.width = '100%';
            if (etaLabel) etaLabel.textContent = '0s';

            document.open();
            document.write(text);
            document.close();
        } 
        catch (err) {
            clearInterval(timer);
            alert('Transcription failed: ' + err.message);
            if (progressBar) progressBar.style.width = '0%';
            if (progressArea) progressArea.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Transcribe';
        }
    });
});