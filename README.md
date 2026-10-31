# QAZAQ LOC QA — Full-Stack Localization QA Platform

**Qazaq Loc QA** — мобильді ойындардың қазақша (`intl_kk.arb`) және өзбекше (`intl_uz.arb`) локализация сапасын тексеретін, қателерді автоматты анықтайтын, маманның редакциялауына (Human Review) мүмкіндік беретін және Flutter `gen-l10n` стандартына сай дайын ARB файлдар мен JSON/HTML есептерін шығаратын кәсіби веб-платформа.

---

## Негізгі мүмкіндіктер

- **ARB және CSV парсері мен валидаторы:** `intl_ru.arb`, `intl_kk.arb`, `intl_uz.arb`, `intl_en.arb` және `glossary.csv` файлдарын Drag & Drop арқылы жүктеу, JSON/ICU синтаксисін тексеру.
- **12 қате түрін анықтау:** `untranslated`, `same_as_source`, `placeholder_mismatch`, `plural_mismatch`, `glossary_violation`, `length_overflow`, `machine_translation_suspect`, `inconsistent_term`, `suffix_harmony`, `orthography`, `wrong_language`, `other_localization_issue`.
- **Қазақ тілінің морфологиялық және орфографиялық тексеруі:**
  - `{name}-ға`, `{name}-ден` сияқты runtime плейсхолдер жалғауларын ұстау, қауіпті авто-түзетуді бұғаттау және сөйлемді қайта құрастыру нұсқасын ұсыну;
  - `ә, ғ, қ, ң, ө, ұ, ү, һ, і` төл әріптерінің орнына жазылған орыс/латын таңбаларын анықтау;
  - Ресми қазақ латын әліпбиіне транслитерациялау және латынша UI ұзындығын есептеу.
- **Глоссарий басқару жүйесі:** Ойын терминдері мен сленгтерін (`фракция`, `отбасы`, `Grand Coins`, `бизнес`, `варн`, `мут`, `фура`, `ГК`) қосу, өзгерту, жою, іздеу, CSV импорт/экспорт.
- **Маман редакторы (Human Review):** Автоматты түзетулер `reviewed_by_human = false` күйінде қалады; тек маман растаған жолдар `reviewed_by_human = true` мәртебесін алып, `@key` метадерегіне (`x-reviewed-by-human: true`) жазылады.
- **Есептер және ARB экспорты:** `intl_kk_fixed.arb`, `intl_uz_fixed.arb`, JSON және автономды Dark-mode HTML есептері.
- **Жоғары өнімділік:** 5 500+ кілті бар ірі ARB файлдарын бірнеше секундта өңдейді.

---

## Жоба құрылымы

```text
qazaq-loc-qa/
├── frontend/          # React + TypeScript + Tailwind CSS + Lucide + Recharts
├── backend/
│   ├── app/           # FastAPI сервері, SQLAlchemy модельдері, NLP және QA қозғалтқышы
│   └── tests/         # Автоматты pytest тесттер жинағы (13 кешенді тест)
├── cli/               # locqa CLI құралы
├── data/demo/         # [DEMO] ретінде белгіленген үлгі ARB файлдары
├── glossary/          # Бастапқы ойын терминдерінің CSV глоссарийі
├── reports/           # Генерацияланған есептер қалтасы
├── docs/              # Архитектуралық құжаттама
├── .github/workflows/ # GitHub Actions CI/CD workflow
├── requirements.txt
├── package.json
└── .env.example
```

---

## Іске қосу нұсқаулығы

### 1. Бір пәрменмен іске қосу (Windows PowerShell)

```powershell
.\start_platform.ps1
```

Немесе Backend пен Frontend-ті екі терминалда бөлек қосу:

### 2. Backend серверін іске қосу (FastAPI — порт 8000)

```powershell
# Виртуалды ортаны белсендіру (немесе жасау)
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Серверді қосу
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
API құжаттамасы (Swagger UI): http://127.0.0.1:8000/docs

### 3. Frontend интерфейсін іске қосу (Vite React — порт 5173)

```powershell
cd frontend
npm install
npm run dev
```
Веб-платформа мекенжайы: http://127.0.0.1:5173

---

## CLI құралын пайдалану

```powershell
# JSON есеп шығару
.\locqa.cmd check --source data/demo/intl_ru.arb --target data/demo/intl_kk.arb --glossary glossary/glossary.csv --out reports/report.json

# JSON + HTML есеп + түзетілген ARB файлын бірден шығару
.\locqa.cmd check --source data/demo/intl_ru.arb --target data/demo/intl_kk.arb --glossary glossary/glossary.csv --out reports/report.json --html reports/report.html --fixed-arb reports/intl_kk_fixed.arb

# Қазақша мәтінді ресми латын әліпбиіне транслитерациялау
.\locqa.cmd transliterate "Қазақша ойын локализациясы: {name}"
```

---

## Автоматты тесттерді іске қосу

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

---

## AI / LLM кілтін қосу (міндетті емес)

Платформа API кілтінсіз-ақ ережелерге негізделген лингвистикалық қозғалтқышпен толық жұмыс істейді. Google Gemini немесе OpenAI API кілтін қосу үшін веб-интерфейстегі **«Баптаулар»** бөлімін ашып, кілтті енгізіп **«Баптауларды сақтау»** батырмасын басыңыз.

## 7. Интернетке жариялау (Vercel + Render + PostgreSQL)

Frontend (Vercel) және FastAPI + PostgreSQL Backend (Render / Docker) бөліктерін бөлек жариялау бойынша толық қадамдық нұсқаулық: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Жарияланғаннан кейін барлық функцияларды тексеру скрипті:
```powershell
.\.venv\Scripts\python.exe scripts/verify_deployment.py --api-url https://<render-api-url> --frontend-url https://<vercel-app-url>
```
