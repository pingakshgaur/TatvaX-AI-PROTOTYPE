# TatvaX v2.6

**A multilingual AI tutor, assessment platform and AI school companion for Indian students.**

Students ask questions by typing or speaking in any of 16 Indian languages, get step-by-step explanations grounded in their school's own study notes, practise with assessments, and track their progress. Teachers get class analytics and edit the notes the tutor teaches from.

[Watch the v1 prototype in action](https://youtu.be/hqo_TAZh0ls)

---

## What's new in version 2.6

- **Review deck**: every question a student gets wrong in an assessment becomes a review card. Cards come back on a widening schedule (today, tomorrow, in 3 days, a week, two weeks) until they are mastered. Mistakes from earlier assessments are added automatically on upgrade.
- **Assignments**: teachers set an assessment or reading for a class, with a due date. Every student answers the same questions (written once, then reshuffled per student), and the Teacher console shows who has finished and their scores.
- **Progress reports**: a printable PDF of a student's level, activity over 30 days, results per subject, recent assessments, badges and review deck. Students download their own from Progress; teachers download any student's from the Students table, for parents or records.
- **Questions with a photo**: attach or paste a picture of a textbook problem. On NVIDIA, photo questions automatically use NVIDIA's free vision model (Nemotron 3.5 Super VL), while text questions stay on the model you chose. Gemini, OpenAI and Claude read photos with their usual models.
- **Reminders**: a "For today" panel on the overview (to-dos due, review cards, unfinished assignments), counts in the sidebar, and a once-a-day reminder about due tasks. To-dos can link to a page, and "Add to to-do" appears on assessment results and on every chapter of the notes.
- **16 languages**: Nepali, Sanskrit and Konkani join the 13 from before.
- **Faster first visit**: pages and the maths renderer load when needed, so the first download is about a third of what it was (703 KB down to 268 KB).
- **Undo**: deleting a to-do, an assessment or a review card can be undone from the notification.
- **School time zone**: streaks, daily goals and due dates follow the school's clock (India by default; set `TATVAX_UTC_OFFSET_MINUTES` elsewhere).
- **Several server processes**: set `TATVAX_SHARED_RATE_LIMIT=1` to keep rate limits in the database so all workers share them.
- **Continuous integration**: GitHub Actions runs the backend tests on Python 3.11 and 3.13 and builds the frontend on every push.
- The interface of the to-do list, assessment history and exports is translated into every language.

## What's new in version 2.5.1

- **Any AI provider**: NVIDIA (unchanged, still the default), Google Gemini, Groq, OpenRouter, OpenAI, Anthropic Claude, Mistral, DeepSeek, Together AI, xAI, a local Ollama, or any OpenAI-compatible server. Each provider keeps its own key and model, and teachers switch between them in **Teacher console > AI settings**. Requests adapt automatically when a model rejects an option (for example `temperature` or `max_tokens`), so new models work without code changes.
- **Faster answers**: reasoning is turned off for NVIDIA models that think before answering, the prompt sends only the relevant notes, and longer assessments are written in parallel batches. In testing, the first words of an answer arrived in about 1.6 s, and a 20-question assessment took about 12 s instead of 60–90 s.
- **TatvAI**: the help desk is now TatvAI, an AI companion for school questions and study help.
- **Subject artwork**: every subject has its own illustration, used as its logo and as the backdrop of its cards everywhere in the app. Gradients are gone.
- **A new Subjects page** with chapters, topics, your questions, average score, notes read and quick links for every subject.
- **To-do list**: tasks with notes, priority, due dates, subjects, tags and steps; views for today, upcoming and overdue; search, sorting, drag-to-reorder, duplicate and bulk actions. A to-do panel in the profile menu shows what's next.
- **Prompt tools**: copy, edit (the conversation continues from the edited question) or re-ask any question, plus copy and clear in the message box.
- **Assessment history**: review any past assessment, retake it with the questions reshuffled, or delete it.
- **PDF exports**: study notes for any subject, and assessment reports with the score, a per-subject breakdown, and every question with the correct answer and explanation.
- **Translator**: all 16 languages are listed on both sides; no more "More" menu.
- **A simpler profile menu**, with language, daily goal, theme and sound moved into **Settings**.

## What's new in version 2

Version 2 is a complete rewrite of the [v1 prototype](https://github.com/pingakshgaur/TatvaX-AI-PROTOTYPE/tree/main).

| Area | v1 prototype | v2 |
|---|---|---|
| Answers | Keyword overlap returned raw paragraphs | An **AI tutor** (open models on NVIDIA's free API) explains step by step, grounded in the school's notes, in the student's language. Without a key, a BM25 search over the notes answers instead. |
| Languages | 8 | **16**: English, Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Nepali, Sanskrit, Konkani |
| Voice | Recorded from the *server's* microphone; crashed on use | Speech recognition **in the browser**; read-aloud uses the browser's voice, or server-generated audio as a fallback |
| Content | `content_library/*.txt` was never loaded (path bug) | Notes stored in a database, editable by teachers, used instantly by the tutor |
| Frontend | HTML/CSS/JS template | **React 18 + Vite**, custom design system, 5 themes, installable PWA with offline notes |
| Accounts | None | Guest mode, accounts, teacher role, progress synced across devices |
| Practice | None | **Assessments**: AI-generated (or from a built-in question bank) with explanations |
| Motivation | None | XP, levels, daily streaks, 10 achievements, weekly class leaderboard |
| Teachers | None | Teacher console: analytics, student table, content editor, feedback inbox |
| Security | Hard-coded secret key, `debug=True` on `0.0.0.0`, feedback (with emails) saved to a public folder | Generated secret, local-only dev server, strict CSP, JSON-only writes (CSRF defence), rate limits, private feedback |
| Tests | None | 90 backend tests, run on every push by GitHub Actions |

Bugs fixed from v1 include: speech output stripped the vowel signs (matras) from every Indic sentence; good translations were thrown away whenever they contained the word "error"; word replacements turned "hardware" into "needs practiceware"; voice input crashed; the app crashed at start-up on a default Windows console.

### Roadmap items delivered

From the v1 roadmap: AI integration (free NVIDIA-hosted models), user authentication and profiles, learning progress tracking, multiple UI themes, PWA offline support, 15+ language support (16 delivered), gamification (points, badges, leaderboards), interactive quizzes and assessments, an analytics dashboard, AI tutor personalisation (by class and language), and a teacher dashboard with a content editor.

---

## Features

**For students**
- **Subject tutor**: mathematics, science, English and social studies, plus any subject a teacher adds. Answers stream in live with rendered maths, and the tutor adapts its explanations to the student's class.
- **Follow-up suggestions**: after every answer, three new, clickable questions that build on it (never repeating what was already asked).
- **TatvAI**: an AI companion for admissions, fees, exams, rules and general study help. School facts come only from the school's information, so it never invents fees, dates or phone numbers.
- **Assessments**: pick several subjects at once, 3–30 questions, easy/medium/hard/mixed difficulty, and three modes: practice (instant feedback), exam (question navigator and flags, marked at the end) and timed. Results show a per-subject breakdown, and one click retries just the mistakes or sends them to the tutor to explain. Every assessment is saved to a history where it can be reviewed, retaken or exported as a PDF report.
- **Study notes**: colour-coded chapter and topic cards with example/remember/formula callouts, reading progress, "mark as read", a quiz per chapter, search and PDF export. Available offline once opened.
- **Translator**: translate as you type between 16 languages (all listed on both sides), with language detection, voice input, read-aloud and history (<kbd>Ctrl</kbd>+<kbd>K</kbd>). Any answer can also be translated in place.
- **Voice**: ask by speaking (with a live microphone level), and listen to any answer.
- **Rewards**: XP and levels, daily streaks, an adjustable daily goal, 13 achievements in four rarities with full-screen celebrations, and a weekly leaderboard (opt-out available).
- **To-do list**: plan homework and revision with priorities, due dates, subjects, tags and steps.
- **Profile menu**: level, XP, daily goal and a to-do panel from the avatar in the top bar, with language, theme, goal and sound in Settings.

**For teachers**
- **AI settings**: choose the AI provider (NVIDIA, Gemini, Groq, OpenRouter, OpenAI, Claude, Mistral, DeepSeek, Together, xAI, Ollama or a custom server), paste its key, load the models it offers and test the connection, with no restart needed.
- Class analytics: active learners, questions per day, subjects, languages, and average assessment scores by subject (lowest first, to show what needs revision).
- A student table with level, XP, questions, assessments, average score and last activity.
- A Markdown content editor with live preview. Add a subject and the tutor, search and assessments use it immediately.
- A feedback inbox.

---

## Quick start

You need **Python 3.10+** and **Node.js 18+**.

```bash
git clone https://github.com/pingakshgaur/TatvaX-AI-PROTOTYPE.git
cd TatvaX-AI-PROTOTYPE

# 1. Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

# 2. Frontend (builds once into frontend/dist, which Flask serves)
cd frontend
npm install
npm run build
cd ..

# 3. Run
python run.py
```

Open **http://localhost:5000**. The first account you create becomes the **teacher/administrator**.

### Turning on the AI tutor

TatvaX works with many AI providers. NVIDIA, Google Gemini and Groq all offer **free API keys**. The default is NVIDIA:

1. Go to [build.nvidia.com](https://build.nvidia.com) and sign in or create a free NVIDIA account.
2. Open your profile menu and choose **API Keys**, then **Generate API Key**. The key starts with `nvapi-`.
3. In TatvaX, sign in as the teacher and open **Teacher console > AI settings**. Paste the key, pick a model, and select **Save**. TatvaX tests the connection right away.

You can also set `NVIDIA_API_KEY` in a `.env` file (see `.env.example`); a key saved in the console takes priority.

| Model | Notes |
|---|---|
| `deepseek-ai/deepseek-v4.1-flash` | Very good at maths and step-by-step reasoning |
| `moonshotai/kimi-k2.6` | Large general model with detailed answers |
| `nvidia/nemotron-3-super-120b-a12b` (default) | Fast general-purpose model, good in Indian languages |
| `google/gemma-4-31b-it` | Strong in Indian languages, but slow on the free tier |
| `mistralai/mistral-large-2-instruct` | Reliable all-rounder |

Any other chat model ID from build.nvidia.com can be entered too.

**Other providers.** In **AI settings**, pick a provider, paste its key and select **Save and use**. TatvaX picks a model the key can use, or select **Load available models** to choose one. Keys can also come from environment variables: `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `TOGETHER_API_KEY`, `XAI_API_KEY` and `TATVAX_CUSTOM_API_KEY`. Ollama needs no key.

Free tiers are meant for prototyping and are rate limited (NVIDIA allows about 40 requests a minute). When a limit is hit, or the key is wrong, students automatically get answers from the study notes instead of an error.

Without a key, TatvaX runs in **notes mode**: answers come from the study notes through search and are translated with free public translation services, and assessments come from the built-in question bank. The status indicator in the top bar shows which mode is active.

---

## Development

Run the API and the React dev server side by side:

```bash
python run.py                    # Flask API on :5000
cd frontend && npm run dev       # React with hot reload on :5173 (proxies /api to :5000)
```

Run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

### Project structure

```
TatvaX/
├── run.py                  # entry point (python run.py, or gunicorn run:app)
├── tatvax/                 # Flask backend
│   ├── __init__.py         # app factory, security headers, serves the React build
│   ├── config.py           # settings from environment variables
│   ├── db.py               # SQLite schema
│   ├── ai.py               # AI providers (NVIDIA, Gemini, OpenAI, Claude, ...): streaming, JSON, fallbacks
│   ├── tutor.py            # answers: AI grounded in notes, or offline search
│   ├── knowledge.py        # content library + BM25 search
│   ├── quiz.py             # assessments (AI-generated or question bank)
│   ├── gamification.py     # XP, levels, streaks, achievements, leaderboard
│   ├── translation.py      # AI, then Google and MyMemory fallbacks
│   ├── speech.py           # in-memory text-to-speech
│   ├── languages.py        # 16 languages + script detection
│   ├── users.py            # accounts and settings
│   ├── api.py              # student API
│   ├── admin.py            # teacher API
│   ├── todos.py            # to-do list API
│   ├── review.py           # review deck (spaced repetition)
│   ├── assignments.py      # work teachers set for a class
│   ├── reports.py          # progress reports
│   └── security.py         # CSRF guard, rate limiting, roles
├── frontend/               # React 18 + Vite
│   ├── src/pages/          # Overview, Subjects, Chat, Assessments, Notes, To-dos, Teacher, print exports
│   ├── src/components/     # Shell, charts, dialogs, UI primitives
│   ├── src/lib/            # API client, i18n, Markdown + KaTeX, voice
│   ├── src/styles/         # design tokens and components
│   └── public/             # service worker, manifest, icons
├── content/
│   ├── subjects/*.md       # study notes (seed the database on first run)
│   ├── helpdesk/*.md       # school information
│   └── quizzes/*.json      # offline question bank
└── tests/
```

### Design system

The interface uses its own design language rather than a component kit:
- **Type**: Source Serif 4 for display headings, IBM Plex Sans (with Plex Sans Devanagari) for the interface, and IBM Plex Mono for labels and data. All fonts are self-hosted.
- **Colour**: ink and paper neutrals, a deep peacock teal as the primary colour, and a single turmeric accent that marks the current item.
- **Surfaces**: flat, with hairline rules, tight 4–6 px corners and no gradients.
- **Themes**: System, Light, Dark, Warm (low glare) and High contrast. Chart colours are validated for contrast in each theme.

---

## API overview

All endpoints are under `/api`. Writes must be JSON.

| Method | Path | Purpose |
|---|---|---|
| GET | `/bootstrap` | Languages, subjects, AI status, current user |
| POST | `/chat` | Ask a question; streams NDJSON events (`start`, `delta`, `replace`, `done`) |
| GET/DELETE | `/conversations[/<id>]`, POST `/conversations/<id>/rewind` | Session history, editing a question |
| POST | `/quiz`, `/quiz/<id>/answer`, `/quiz/<id>/submit`, `/quiz/<id>/retry`, `/quiz/<id>/retake` | Assessments |
| GET/DELETE | `/quizzes`, `/quiz/<id>` | Assessment history and review |
| GET/POST/PATCH/DELETE | `/todos[/<id>]`, POST `/todos/reorder`, `/todos/bulk`, `/todos/<id>/duplicate` | To-do list |
| GET | `/subjects/overview` | Per-subject facts for the Subjects page |
| GET/POST/DELETE | `/review`, `/review/all`, `/review/<id>` | Review deck: due cards, answer a card, remove a card |
| GET/POST | `/assignments`, `/assignments/<id>/start`, `/assignments/<id>/done` | A student's assignments |
| GET/POST/PATCH/DELETE | `/admin/assignments[/<id>]` | Setting assignments and following progress |
| GET | `/report`, `/admin/students/<id>/report` | Progress reports |
| GET | `/todos/summary` | To-dos due today or overdue, for reminders |
| GET | `/progress`, `/leaderboard` | Progress and gamification |
| GET | `/library[/<slug>]`, `/search?q=` | Study notes |
| POST | `/translate`, `/tts` | Translation and speech |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Accounts |
| GET/PATCH | `/me` | Profile and settings |
| POST | `/feedback` | Feedback |
| GET | `/admin/overview`, `/admin/students`, `/admin/feedback` | Teacher analytics |
| GET/POST/PUT/DELETE | `/admin/documents[/<slug>]` | Content editor |
| GET/PUT | `/admin/ai`, GET `/admin/ai/models`, `/admin/ai/key`, POST `/admin/ai/test` | AI providers, keys, models and connection test |

---

## Deployment

The `Procfile` runs gunicorn with threads, which streaming answers need:

```
build:  pip install -r requirements.txt && cd frontend && npm ci && npm run build
start:  gunicorn "run:app" --worker-class gthread --threads 8 --timeout 180
```

Set `TATVAX_SECRET_KEY`, `TATVAX_SECURE_COOKIES=1` (on HTTPS) and `TATVAX_BEHIND_PROXY=1` (behind a proxy), and give the server a persistent disk for `instance/`. That folder holds the SQLite database, including any AI keys saved from the console, so keep it private. Rate limits are kept in memory by default; if you run several worker processes (for example `gunicorn -w 4`), set `TATVAX_SHARED_RATE_LIMIT=1` so they share limits through the database. Set `TATVAX_UTC_OFFSET_MINUTES` if the school is outside India.

---

## Known limitations

- TatvaX stores data in SQLite, which comfortably serves one school on one server. A multi-school deployment would need a move to a database server such as PostgreSQL, which is not built in yet.
- Photos are sent to the AI provider to be answered and are not stored. With NVIDIA, Gemini, OpenAI or Claude they work out of the box; other providers need a model that accepts images.
- Nepali, Sanskrit and Konkani have the main screens translated; voice input for Sanskrit and Konkani depends on the browser.

- Voice *input* uses the browser's Web Speech API, which works in Chrome and Edge but not Firefox. Read-aloud falls back to server-generated audio when the device has no voice for a language; Odia and Assamese only work on devices that provide their own voice.
- The interface is fully translated into English. The other 12 languages cover the main screens and fall back to English for the rest; review by native speakers is welcome. AI answers are fully in the chosen language.
- Notes mode translates with free public endpoints, which can be rate limited.

---

## License

MIT. See [LICENSE](LICENSE).
