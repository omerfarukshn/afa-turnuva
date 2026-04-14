# AFA Futbol Turnuvası — Puan Tablosu

**Samsun Alman Futbol Akademisi** turnuva puan tablosu ve yönetim paneli.

- Admin paneli: maç/takım ekleme, düzenleme, silme
- Public sayfa: canlı puan tablosu (TFF kuralları: puan → ikili averaj → genel averaj → atılan gol)
- Stack: Flask 3 + SQLAlchemy + SQLite (ya da Postgres) + Bootstrap 5

---

## Lokal Çalıştırma

```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```

**Admin giriş (varsayılan):** `admin` / `admin123`
Üretime çıkmadan önce `TFF_ADMIN_PASS` env var ile değiştir.

---

## Env Variables

| Değişken | Amaç | Zorunlu |
|---|---|---|
| `TFF_SECRET_KEY` | Flask session imzası | Prod'da zorunlu |
| `TFF_ADMIN_USER` | Admin kullanıcı adı | Varsayılan: `admin` |
| `TFF_ADMIN_PASS` | Admin şifresi (plaintext env, hash'e çevrilir) | Prod'da zorunlu |
| `DATABASE_URL` | Postgres URL (örn. Neon) | Opsiyonel |
| `DATABASE_PATH` | SQLite dosya yolu (Fly.io volume: `/data/database.db`) | Opsiyonel |

---

## Deploy — 3 Seçenek

### Seçenek 1: Fly.io (Önerilen — tamamen ücretsiz + kalıcı SQLite)

```bash
# Tek seferlik: Fly CLI kur
# Windows: iwr https://fly.io/install.ps1 -useb | iex

flyctl auth signup       # veya: flyctl auth login
flyctl launch --no-deploy # fly.toml'u doğrula
flyctl volumes create afa_data --size 1 --region fra
flyctl secrets set TFF_SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
flyctl secrets set TFF_ADMIN_PASS="GÜÇLÜ_ŞİFRE_BURAYA"
flyctl deploy
```

Çıkan URL: `https://afa-turnuva.fly.dev`
**Cloudflare DNS:** Domain gelince → Cloudflare'de `CNAME → afa-turnuva.fly.dev` + `flyctl certs add yourdomain.com`.

### Seçenek 2: Render.com (GitHub push = otomatik deploy)

1. GitHub'a push et
2. [render.com](https://render.com) → New → Web Service → GitHub reponu bağla
3. `render.yaml` otomatik okunur
4. **DİKKAT:** Ücretsiz plan disk desteklemez → SQLite restart'ta silinir.
   - Çözüm A: `plan: starter` ($7/ay) + persistent disk → dosya hep burada
   - Çözüm B: [Neon.tech](https://neon.tech) ücretsiz Postgres → `DATABASE_URL` secret olarak ekle, `requirements.txt`'ye `psycopg2-binary==2.9.9` ekle

### Seçenek 3: PythonAnywhere (basit ama custom domain ücretli)

Flask + SQLite desteği tam. `username.pythonanywhere.com` ücretsiz. Custom domain için $5/ay.

---

## GitHub → Cloudflare DNS Akışı

1. `git init && git add . && git commit -m "initial"` → GitHub'a push
2. Deploy'u yap (Fly.io veya Render)
3. Alan adı netleşince:
   - Cloudflare hesabında domain ekle (Cloudflare nameserver'larına geçiş)
   - DNS sekmesi → yeni CNAME: `@ → afa-turnuva.fly.dev` (ya da Render URL)
   - SSL/TLS: "Full" moduna al
   - Deploy tarafında custom domain sertifikası ekle

---

## TODO (Deploy sonrası)

- [ ] Güçlü `TFF_ADMIN_PASS` set et
- [ ] Rastgele `TFF_SECRET_KEY` üret (`python -c "import secrets;print(secrets.token_hex(32))"`)
- [ ] `debug=False` otomatik (gunicorn production modda)
- [ ] Alan adı gelince Cloudflare DNS + SSL
- [ ] (Opsiyonel) CSRF token için Flask-WTF
- [ ] (Opsiyonel) Rate limiting: Flask-Limiter
