# TFF Lig Yönetim Sistemi - Yapılacaklar Listesi

## [x] 1. Proje Yapısını Oluştur (Tamamlandı)
- [x] Ana proje klasörü: `tff-lig-yonetim/`
- [x] TODO.md dosyası oluştur

## [ ] 2. Bağımlılıklar ve Temel Dosyalar
- [ ] `requirements.txt` oluştur
- [ ] `app.py` (temel Flask setup)
- [ ] `models.py` (Team, Match modelleri)
- [ ] DB init fonksiyonu

## [ ] 3. Backend Logic
- [ ] Puan hesaplama fonksiyonu (`calculate_standings`)
- [ ] Admin routes (login, teams, matches)
- [ ] Public route (puan tablosu)
- [ ] Otomatik trigger (maç değişikliklerinde recalc)

## [ ] 4. Templates (Bootstrap 5)
- [ ] `templates/base.html`
- [ ] `templates/index.html` (puan tablosu)
- [ ] `templates/admin.html`
- [ ] `templates/admin_login.html`

## [ ] 5. Static Assets
- [ ] `static/css/custom.css` (TFF-style)
- [ ] `static/js/app.js` (sorting, validation)

## [ ] 6. Test & Demo
- [ ] `python app.py` ile test
- [ ] Browser ile kontrol
- [ ] Örnek veri ekle

**Durum: Backend → Frontend → Test**
