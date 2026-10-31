# QAZAQ LOC QA — Интернетке жариялау нұсқаулығы (GitHub + Render + Vercel)

Бұл нұсқаулық **Qazaq Loc QA** платформасының Frontend (React + Vite) және Backend (FastAPI + PostgreSQL) бөліктерін интернетке бөлек, қауіпсіз және тұрақты түрде жариялау қадамдарын сипаттайды.

---

## Архитектуралық схема (Production)

- **Frontend (UI):** **Vercel** (`https://<сіздің-жобаңыз>.vercel.app`) — статикалық CDN + SPA routing (`vercel.json`).
- **Backend (API):** **Render Web Service** (`https://<сіздің-api>.onrender.com`) — FastAPI (`uvicorn backend.app.main:app`).
- **Тұрақты дерекқор:** **Render Managed PostgreSQL** немесе **Neon / Supabase PostgreSQL** (`DATABASE_URL` автоматты түрде `postgresql+psycopg://` форматына түрлендіріледі).
  - *Ескерту:* Жергілікті компьютерде `DATABASE_URL` берілмесе, жүйе автоматты түрде `data/qazaq_locqa.db` (SQLite) базасымен жұмысын жалғастырады.

---

## 1-қадам: Жобаны GitHub репозиторийіне жүктеу

1. Егер компьютеріңізде Git орнатылмаған болса, [git-scm.com](https://git-scm.com/download/win) немесе **GitHub Desktop** орнатыңыз.
2. [github.com/new](https://github.com/new) бетінде жаңа репозиторий ашыңыз (мысалы: `qazaq-loc-qa`). **Add a README** немесе **.gitignore** құсбелгілерін қоймаңыз (жобада дайын).
3. Терминалда жоба бумасын ашып, мына командаларды орындаңыз:

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\qazaq-loc-qa

git init
git branch -M main
git add .
git status   # Тексеріңіз: .env, *.db, .venv, node_modules тізімде БОЛМАУЫ тиіс!
git commit -m "feat: Qazaq Loc QA full-stack platform ready for cloud deployment"
git remote add origin https://github.com/<ПАЙДАЛАНУШЫ_АТЫ>/qazaq-loc-qa.git
git push -u origin main
```

> **Қауіпсіздік кепілдігі:** Түбірлік `.gitignore` файлы `.env`, `*.db`, `data/uploads/*`, `.venv/` және `node_modules/` файлдарын GitHub-қа жіберуден автоматты түрде блоктайды.

---

## 2-қадам: FastAPI Backend пен PostgreSQL дерекқорын Render-ге жариялау

### А нұсқасы (Ұсынылады — `render.yaml` Blueprint арқылы 1 батырмамен):
1. [dashboard.render.com](https://dashboard.render.com) сайтына кіріп, **New +** -> **Blueprint** таңдаңыз.
2. GitHub аккаунтыңызды жалғап, `qazaq-loc-qa` репозиторийін таңдаңыз.
3. Render жобадағы `render.yaml` файлын автоматты түрде оқып, бірден **2 ресурс** құрады:
   - `qazaq-locqa-db` — тұрақты **PostgreSQL** дерекқоры.
   - `qazaq-locqa-api` — **FastAPI** веб-сервисі (`DATABASE_URL` автоматты жалғанады).
4. Сұралған құпия айнымалыларды толтырыңыз (қалауыңызша бос қалдыруға болады):
   - `CORS_ORIGINS`: кейінірек Vercel URL шыққанда қосасыз (әдепкі `CORS_ORIGIN_REGEX=^https://.*\.vercel\.app$` барлық `*.vercel.app` домендерін бірден өткізеді).
   - `LLM_API_KEY`: Gemini немесе OpenAI кілті (бос қалдырсаңыз, ережеге негізделген QA қозғалтқышы толық жұмыс істейді).
5. **Apply** батырмасын басыңыз. Іске қосылған соң API сілтемесін көшіріп алыңыз (мысалы: `https://qazaq-locqa-api.onrender.com`).

### Ә нұсқасы (Қолмен баптау немесе Neon.tech тегін шексіз PostgreSQL қолдану):
Егер тегін мерзімі шектелмейтін PostgreSQL қаласаңыз, [neon.tech](https://neon.tech) немесе [supabase.com](https://supabase.com) сайтынан PostgreSQL ашып, оның `postgresql://...` сілтемесін Render-дегі **New + -> Web Service** ішіне қойыңыз:
- **Build Command:** `pip install --upgrade pip && pip install -r backend/requirements.txt`
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/health`
- **Environment Variables:**
  - `DATABASE_URL` = `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`
  - `APP_ENV` = `production`
  - `CORS_ORIGIN_REGEX` = `^https://.*\.vercel\.app$`
  - `LLM_API_KEY` = *(міндетті емес, тек Render ішінде сақтаңыз)*

Тексеру үшін браузерден ашыңыз: `https://qazaq-locqa-api.onrender.com/api/health`
Жауап: `{"status":"ok","platform":"Qazaq Loc QA","version":"1.0.0","environment":"production","database":"postgresql"}`.

---

## 3-қадам: React Frontend-ті Vercel-ге жариялау

1. [vercel.com/new](https://vercel.com/new) бетіне кіріп, GitHub-тағы `qazaq-loc-qa` репозиторийін **Import** жасаңыз.
2. **Configure Project** терезесінде:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend` *(Ескерту: егер `./` түбірлік буманы қалдырсаңыз да, түбірлік `vercel.json` оны автоматты жинайды)*.
3. **Environment Variables** бөліміне мына айнымалыны қосыңыз:
   - **Key:** `VITE_API_BASE_URL`
   - **Value:** `https://qazaq-locqa-api.onrender.com` *(2-қадамдағы Render URL сілтемеңіз, соңында `/` белгісінсіз)*.
4. **Deploy** батырмасын басыңыз! 30–60 секунд ішінде дайын домен беріледі (мысалы: `https://qazaq-loc-qa.vercel.app`).
5. *(Қосымша)* Өз жеке доменіңізді қоссаңыз, Render -> `qazaq-locqa-api` -> **Environment** ішіндегі `CORS_ORIGINS` мәніне сол доменді жазып сақтаңыз.

---

## 4-қадам: Жарияланғаннан кейін толық тексеру (Post-Deploy Verification)

Жарияланған платформаның барлық 8 негізгі функциясын бір командамен автоматты тексеру үшін:

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\qazaq-loc-qa

.\.venv\Scripts\python.exe scripts/verify_deployment.py `
  --api-url https://qazaq-locqa-api.onrender.com `
  --frontend-url https://qazaq-loc-qa.vercel.app `
  --origin https://qazaq-loc-qa.vercel.app
```

Скрипт мыналарды автоматты тексереді және уақытша тест деректерін базадан тазалайды:
1. Frontend SPA HTML жүктелуі (`HTTP 200`).
2. Backend `/api/health` және PostgreSQL байланысы.
3. Cross-Origin CORS заголовктары (`Origin` және `Content-Disposition`).
4. ARB және CSV файлдарын жүктеу + жарамсыз JSON-ды кері қайтару.
5. QA талдауын іске қосу және Dashboard статистикасын базадан оқу.
6. Қазақ тіліндегі `{name}-ға` динамикалық жалғау қорғанысы мен Human Review сақталуы.
7. CAT редактор және латын транслитерациясы.
8. JSON есеп, HTML есеп және `intl_kk_fixed.arb` экспорты.
