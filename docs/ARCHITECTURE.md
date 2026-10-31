# QAZAQ LOC QA — Архитектуралық және лингвистикалық құжаттама

## 1. Жүйелік архитектура

**Qazaq Loc QA** — мобильді ойындардың (Flutter / ARB стандарты) қазақша (`intl_kk.arb`) және өзбекше (`intl_uz.arb`) локализация сапасын тексеретін толыққанды Full-Stack веб-платформа және CLI құралы.

- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Recharts, Vite.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite (WAL режимі).
- **AI / NLP қабаты:**
  - 12 қате түрін анықтайтын детерминистік және лингвистикалық ережелер қозғалтқышы (`qa_engine.py`, `kazakh_nlp.py`, `uzbek_nlp.py`).
  - Қосымша LLM интеграциясы (`llm_service.py` — Google Gemini немесе OpenAI-үйлесімді API). API кілті тек Backend базасында сақталады және логқа жазылмайды.

## 2. Анықталатын 12 қате түрі

1. `untranslated` — аударылмаған немесе бос жолдар.
2. `same_as_source` — түпнұсқамен бірдей қалған жолдар (брендтер мен рұқсат етілген ойын сленгі ескерілмейді).
3. `placeholder_mismatch` — `{name}`, `{count}`, `%s`, `$1` плейсхолдерлерінің жоғалуы немесе өзгеруі.
4. `plural_mismatch` — ICU `plural` / `select` жақшаларының немесе міндетті `other{...}` тармағының бұзылуы.
5. `glossary_violation` — бекітілген глоссарий терминдерін (`отбасы`, `Grand Coins`, `фракция`, `варн`, `мут`, `фура`, `ГК`) бұзу.
6. `length_overflow` — UI батырмалары мен қысқа өрістердің тым ұзын болуы (кирилл және ресми қазақ латын әліпбиіндегі ұзындықты қоса тексереді).
7. `machine_translation_suspect` — сөзбе-сөз калькаланған машиналық аударма белгілері.
8. `inconsistent_term` — бірдей түпнұсқа мәтіннің әр кілтте әртүрлі аударылуы.
9. `suffix_harmony` — қазақ тіліндегі үндестік заңының бұзылуы және `{name}-ға` сияқты runtime плейсхолдерден кейінгі қауіпті жалғаулар.
10. `orthography` — қазақтың төл әріптерінің (`ә, ғ, қ, ң, ө, ұ, ү, һ, і`) орыс/латын ұқсас әріптерімен алмасуы.
11. `wrong_language` — мақсатты файлда басқа тілде жазылған мәтін.
12. `other_localization_issue` — HTML/RichText тегтерінің (`<color=...>`) немесе жол тасымалының (`\n`) сәйкессіздігі.

## 3. Динамикалық плейсхолдерлерге жалғау жалғау (`KazakhSuffixHelper` үлгісі)

Егер ойын кодында `{name}` айнымалысына қосымша жалғау міндетті болса, сөйлемді қайта құрастыру (`Сыйлық {name} атты ойыншыға жіберілді`) немесе код деңгейінде дыбыс үндестігін есептеу ұсынылады:

```dart
String attachDativeKazakh(String name) {
  final trimmed = name.trim();
  if (trimmed.isEmpty) return name;
  const frontVowels = {'ә', 'е', 'і', 'ө', 'ү', 'и', 'э', 'e', 'i'};
  const voiceless = {'к', 'қ', 'п', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'k', 'p', 's', 't'};
  final lower = trimmed.toLowerCase();
  final lastChar = lower[lower.length - 1];
  bool isFront = false;
  for (int i = lower.length - 1; i >= 0; i--) {
    if (frontVowels.contains(lower[i])) { isFront = true; break; }
    if ({'а', 'о', 'ұ', 'ы', 'я', 'у', 'a', 'o', 'u'}.contains(lower[i])) { isFront = false; break; }
  }
  if (voiceless.contains(lastChar)) {
    return '$name-${isFront ? "ке" : "қа"}';
  }
  return '$name-${isFront ? "ге" : "ға"}';
}
```

## 4. Flutter `gen-l10n` ARB экспорт стандарты

Экспортталған `intl_kk_fixed.arb` файлында:
- Барлық бастапқы кілттер мен реттілік сақталады;
- Өзгермеген жолдарға тиіспейді;
- `@key` ішіндегі `description` және `placeholders` толық сақталады;
- Адам тексерген жолдарға ARB стандартына сай `x-reviewed-by-human: true`, `x-qa-status: "verified"` vendor-метадеректері қосылады (Flutter компиляциясына кедергі келтірмейді).
