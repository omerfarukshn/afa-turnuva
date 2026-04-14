/**
 * AFA Futbol Turnuvası - Interactive JS
 */

document.addEventListener('DOMContentLoaded', function () {
    // Fotoğraf lightbox (match_detail.html)
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
        photoModal.addEventListener('show.bs.modal', function (event) {
            const trigger = event.relatedTarget;
            if (!trigger) return;
            document.getElementById('photoModalImg').src = trigger.dataset.full;
            document.getElementById('photoModalCaption').textContent = trigger.dataset.caption || '';
        });
    }

    // Tablo satır animasyonu
    if (document.querySelector('.tff-table')) {
        const rows = document.querySelectorAll('.tff-table tbody tr');
        rows.forEach((row, index) => {
            row.style.opacity = '0';
            row.style.transform = 'translateY(10px)';
            row.style.transition = 'all 0.4s ease';
            setTimeout(() => {
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }, 40 * index);
        });
    }
});
