# منصة الفيديو — Professional Video Platform

منصة ويب عربية (RTL) لعرض وإدارة الفيديوهات من مصادر خارجية (YouTube، Google Drive، Vimeo، Dropbox، روابط MP4 مباشرة، Embed)، مع **لوحة إدارة Desktop احترافية** تعمل على Windows (تدعم **اسم القناة/المنتج** و**تحديد تاريخ النشر يدويًا**)، و**REST API** كاملة.

> MVP قابل للاستخدام فعليًا وقابل للتوسع إلى منصة فيديو متكاملة. لا يتم رفع أي فيديو للسيرفر — تُدار الروابط فقط عبر نظام Providers قابل للتوسعة.

---

## المكونات

```text
video-platform/
├── frontend/        Next.js 15 + React 19 + TypeScript + Tailwind (الموقع العام)
├── backend/         FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL (REST API)
├── desktop-admin/   PySide6 (لوحة إدارة Windows)
├── database/        ملفات قاعدة البيانات المساعدة
├── docker/          Nginx reverse proxy
├── docs/            الوثائق التقنية
├── scripts/         نسخ احتياطي / استعادة / اختبارات تكامل
├── docker-compose.yml
└── .env.example
```

## المزايا

- 🌐 **موقع عام**: بحث مع Autocomplete (يشمل عنوان/وصف/تصنيف/وسوم/**اسم القناة**)، تصنيفات **هرمية** (أب/أبناء)، قوائم تشغيل مرقّمة، صفحة مشاهدة بمشغل موحد (iframe/HTML5 حسب المصدر)، مشاركة اجتماعية، Dark/Light mode.
- 🔍 **SEO كامل**: Metadata لكل صفحة، Open Graph، Twitter Card، JSON-LD `VideoObject`، `sitemap.xml`، `robots.txt`، Slugs عربية صديقة لمحركات البحث.
- 🖥️ **لوحة Desktop**: Dashboard بإحصائيات ورسم بياني، إدارة فيديوهات بجدول بحث/فلترة/ترتيب/إجراءات جماعية، نافذة «فحص الرابط» مع معاينة تلقائية للصورة والـEmbed، إدارة تصنيفات ووسوم وقوائم تشغيل **بالسحب والإفلات**، مستخدمون بأدوار، سجل عمليات، اختصارات لوحة مفاتيح، إشعارات Toast، رسائل أخطاء عربية ودية + Log file.
- 🔐 **أمان**: JWT (Access+Refresh)، Argon2id لتجزئة كلمات المرور، RBAC (admin/editor/moderator)، Rate limiting، CORS مضبوط، Security headers، Input validation شامل.
- 📊 **تحليلات**: مشاهدات يومية، أكثر الفيديوهات، توزيع حسب المصدر/التصنيف. عدّاد مشاهدات مع dedupe لكل جلسة (ساعة) وتخزين IP **مُجزَّأ فقط** (لا IPs خام).
- 🗄️ **بيانات**: PostgreSQL + Alembic migrations + Soft delete للفيديوهات + Audit logs.

## التشغيل السريع (Docker)

> المتطلبات: Docker + Docker Compose

```bash
git clone <repo-url>
cd video-platform

cp .env.example .env        # ثم عدّل كلمات المرور و JWT_SECRET
docker compose up -d --build
```

عند أول تشغيل أنشئ حساب المدير وأدخل بيانات تجريبية (اختياري):

```bash
docker compose exec backend python -m scripts.seed            # حساب admin من .env
docker compose exec backend python -m scripts.seed --demo     # محتوى تجريبي
```

| الخدمة | العنوان |
|---|---|
| الموقع | http://localhost:6688 |
| API | http://localhost:6688/api/v1 |
| Swagger | http://localhost:6688/docs |

## التشغيل بدون Docker (تطوير)

### 1) Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt

# على Windows بدون Postgres يمكن التجربة بـ SQLite:
set DATABASE_URL=sqlite:///./local_dev.db
python -m scripts.seed --init-tables --demo
uvicorn app.main:app --reload --port 8000
```

مع PostgreSQL فعلي: اضبط `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` ثم:

```bash
alembic upgrade head
```

الاختبارات (تعمل بـ SQLite معزولة):

```bash
python -m pytest tests -q          # 44 اختبار
```

### 2) Frontend

```bash
cd frontend
npm install
set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                        # http://localhost:3000
```

للإنتاج: `npm run build` ثم `npm run start`.

### 3) Desktop Admin

```bash
cd desktop-admin
pip install -r requirements.txt
python main.py
```

- عند أول تشغيل: أدخل عنوان الخادم (افتراضي `http://localhost/api/v1`) واسم المستخدم وكلمة المرور.
- الاختصارات: `Ctrl+N` فيديو جديد · `F5` تحديث · `Ctrl+F` البحث.
- ملف السجل: `%APPDATA%\VideoPlatformAdmin\logs\app.log`

## النسخ الاحتياطي (plan §35)

```bash
# Linux/macOS
scripts/backup.sh                          # أو مع مجلد: ./backup.sh /path/to/dir
scripts/restore.sh backups/video_platform_YYYYmmdd_HHMMSS.sql.gz
```

```powershell
# Windows
powershell -File scripts/backup.ps1
```

يحتفظ السكربت بالنَسخ لمدة 14 يومًا افتراضيًا (`KEEP_DAYS`).

## الأدوار والصلاحيات

| العملية | admin | editor | moderator |
|---|:-:|:-:|:-:|
| إنشاء/تعديل فيديو·تصنيف·وسم·قائمة | ✓ | ✓ | ✗ |
| نشر / إلغاء نشر / أرشفة | ✓ | ✓ | ✓ |
| حذف نهائي (hard) | ✓ | ✗ | ✗ |
| إدارة المستخدمين وسجل العمليات | ✓ | ✗ | ✗ |

## نظام مصادر الفيديو (VideoProvider)

كل مصدر يطبّق واجهة موحدة: كشف الرابط → استخراج ID → توليد Embed URL → جلب الصورة المصغرة عند توفرها → تحديد طريقة التشغيل.

| المصدر | Embed | صورة تلقائية | ملاحظات |
|---|---|---|---|
| YouTube | `/embed/{id}` | ✓ | watch / youtu.be / shorts |
| Google Drive | `/file/d/{id}/preview` | ✗ | يتطلب مشاركة «أي شخص لديه الرابط» |
| Vimeo | `player.vimeo.com/video/{id}` | ✗ | |
| Dropbox | رابط مباشر `raw=1` | ✗ | يعمل كمشغل HTML5 للملفات المرئية |
| Direct URL | HTML5 `<video>` | ✗ | mp4/webm/m3u8... |
| Embed URL | iframe عام | ✗ | بعض المواقع تمنع التضمين |

روابط غير قابلة للتضمين → رسالة واضحة للمدير مع زر «فتح المصدر الأصلي» في الموقع.

## متغيرات البيئة

انظر `.env.example`. أهم المتغيرات:

| المتغير | الوصف |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://user:pass@postgres:5432/db` |
| `JWT_SECRET` | سر طويل عشوائي (32+ حرفًا) |
| `CORS_ORIGINS` | نطاقات الواجهة مفصولة بفواصل |
| `NEXT_PUBLIC_API_URL` | عنوان API كما يراه المتصفح |
| `NEXT_PUBLIC_SITE_NAME` / `NEXT_PUBLIC_SITE_URL` | اسم ونطاق الموقع (SEO) |
| `APP_PORT` | منفذ Nginx الخارجي |

⚠️ لا تضع أي Secrets داخل Git — `.env` مستثنى في `.gitignore`.

## هيكل API

```
POST /api/v1/auth/login|refresh|logout      GET /api/v1/auth/me
GET  /api/v1/videos                         ?q=&category=&tag=&sort=&page=
GET  /api/v1/videos/slug/{slug}             POST /api/v1/videos/{id}/view
POST /api/v1/videos/check-url               POST /api/v1/videos/bulk
POST /api/v1/videos/{id}/publish|unpublish|archive|duplicate
PUT/DELETE /api/v1/videos/{id}[?hard=true]
GET/POST/PUT/DELETE /api/v1/categories[...] PUT /categories/reorder/all
GET/POST/PUT/DELETE /api/v1/tags[...]
GET/POST/PUT/DELETE /api/v1/playlists[...]  PUT /playlists/{id}/videos
CRUD /api/v1/users                          PATCH /users/{id}/password
GET  /api/v1/analytics/dashboard|views/daily|top-videos|by-source|by-category
GET  /api/v1/audit-logs                     GET /api/v1/providers
```

كل الاستجابات بصيغة موحدة: `{ "success": bool, "message": "...", "data": ... }` والأخطاء `{ "success": false, "message": "...", "error_code": "..." }`.

## الاختبارات والجودة

```bash
cd backend && python -m pytest tests -q       # Unit + API + Auth + Providers
# بعد تشغيل الخادم:
python ../scripts/integration_check.py        # تكامل API شامل
# بعد تشغيل الواجهة:
python ../scripts/frontend_smoke.py           # فحص عرض الصفحات
```

آخر نتائج مسجلة أثناء التطوير: **44/44 backend · 24/24 integration · 16/16 frontend smoke**.

## خارطة الطريق (خارج نطاق MVP)

رفع فيديوهات + Transcoding، بث مباشر، اشتراكات، تعليقات، توصيات ذكية، تطبيق موبايل، CDN خاص، دعم إنجليزي LTR (البنية جاهزة عبر `src/lib/i18n/`).

## الترخيص

MIT — انظر [LICENSE](LICENSE).
