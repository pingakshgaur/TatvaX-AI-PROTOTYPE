# TatvaX v2

**A multilingual AI tutor, assessment platform and school help desk for Indian students.**

Students ask questions by typing or speaking in any of 13 Indian languages, get step-by-step explanations grounded in their school's own study notes, practise with assessments, and track their progress. Teachers get class analytics and edit the notes the tutor teaches from.

[Watch the v1 prototype in action](https://youtu.be/hqo_TAZh0ls)

---

## What's new in version 2

Version 2 is a complete rewrite of the [v1 prototype](https://github.com/pingakshgaur/TatvaX-AI-PROTOTYPE/tree/main).

| Area | v1 prototype | v2 |
|---|---|---|
| Answers | Keyword overlap returned raw paragraphs | An **AI tutor** (open models on NVIDIA's free API) explains step by step, grounded in the school's notes, in the student's language. Without a key, a BM25 search over the notes answers instead. |
| Languages | 8 | **13**: English, Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu |
| Voice | Recorded from the *server's* microphone; crashed on use | Speech recognition **in the browser**; read-aloud uses the browser's voice, or server-generated audio as a fallback |
| Content | `content_library/*.txt` was never loaded (path bug) | Notes stored in a database, editable by teachers, used instantly by the tutor |
| Frontend | HTML/CSS/JS template | **React 18 + Vite**, custom design system, 5 themes, installable PWA with offline notes |
| Accounts | None | Guest mode, accounts, teacher role, progress synced across devices |
| Practice | None | **Assessments**: AI-generated (or from a built-in question bank) with explanations |
| Motivation | None | XP, levels, daily streaks, 10 achievements, weekly class leaderboard |
| Teachers | None | Teacher console: analytics, student table, content editor, feedback inbox |
| Security | Hard-coded secret key, `debug=True` on `0.0.0.0`, feedback (with emails) saved to a public folder | Generated secret, local-only dev server, strict CSP, JSON-only writes (CSRF defence), rate limits, private feedback |
| Tests | None | 41 backend tests |

Bugs fixed from v1 include: speech output stripped the vowel signs (matras) from every Indic sentence; good translations were thrown away whenever they contained the word "error"; word replacements turned "hardware" into "needs practiceware"; voice input crashed; the app crashed at start-up on a default Windows console.

### Roadmap items delivered

From the v1 roadmap: AI integration (free NVIDIA-hosted models), user authentication and profiles, learning progress tracking, multiple UI themes, PWA offline support, 15+ language support (13 delivered), gamification (points, badges, leaderboards), interactive quizzes and assessments, an analytics dashboard, AI tutor personalisation (by class and language), and a teacher dashboard with a content editor.

---

## Features

**For students**
- **Subject tutor**: mathematics, science, English and social studies, plus any subject a teacher adds. Answers stream in live with rendered maths, and the tutor adapts its explanations to the student's class.
- **School help desk**: admissions, fees, exams and rules. The help desk answers only from the school's information and never invents fees, dates or phone numbers.
- **Assessments**: 5 or 10 questions, three difficulty levels, an optional topic, and instant explanations. One click sends the wrong answers to the tutor to explain.
- **Study notes**: a reader with a table of contents and search, available offline once opened.
- **Voice**: ask by speaking, and listen to any answer.
- **Progress**: XP and levels, daily streaks, achievements, 14-day activity, and a weekly leaderboard (opt-out available).
- **Quick translate** with <kbd>Ctrl</kbd>+<kbd>K</kbd>.

**For teachers**
- **AI settings**: paste a free NVIDIA API key, choose the model and test the connection, with no restart needed.
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

### Turning on the AI tutor (free NVIDIA key)

TatvaX's AI tutor runs on open models hosted by NVIDIA, which offers **free developer API keys**:

1. Go to [build.nvidia.com](https://build.nvidia.com) and sign in or create a free NVIDIA account.
2. Open your profile menu and choose **API Keys**, then **Generate API Key**. The key starts with `nvapi-`.
3. In TatvaX, sign in as the teacher and open **Teacher console > AI settings**. Paste the key, pick a model, and select **Save**. TatvaX tests the connection right away.

You can also set `NVIDIA_API_KEY` in a `.env` file (see `.env.example`); a key saved in the console takes priority.

| Model | Notes |
|---|---|
| `google/gemma-4-31b-it` (default) | Strong in Indian languages, fast |
| `deepseek-ai/deepseek-v4.1-flash` | Very good at maths and step-by-step reasoning |
| `moonshotai/kimi-k2.6` | Large general model with detailed answers |
| `nvidia/nemotron-3-super-120b-a12b` | NVIDIA's general-purpose model |
| `mistralai/mistral-large-2-instruct` | Reliable all-rounder |

Any other chat model ID from build.nvidia.com can be entered too.

NVIDIA's free tier is meant for prototyping and is rate limited (about 40 requests a minute). When a limit is hit, or the key is wrong, students automatically get answers from the study notes instead of an error.

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
│   ├── ai.py               # NVIDIA API client: streaming, JSON output, error fallbacks
│   ├── tutor.py            # answers: AI grounded in notes, or offline search
│   ├── knowledge.py        # content library + BM25 search
│   ├── quiz.py             # assessments (AI-generated or question bank)
│   ├── gamification.py     # XP, levels, streaks, achievements, leaderboard
│   ├── translation.py      # AI, then Google and MyMemory fallbacks
│   ├── speech.py           # in-memory text-to-speech
│   ├── languages.py        # 13 languages + script detection
│   ├── users.py            # accounts and settings
│   ├── api.py              # student API
│   ├── admin.py            # teacher API
│   └── security.py         # CSRF guard, rate limiting, roles
├── frontend/               # React 18 + Vite
│   ├── src/pages/          # Overview, Subjects, Chat, Assessments, Notes, Progress, Teacher
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
| GET/DELETE | `/conversations[/<id>]` | Session history |
| POST | `/quiz`, `/quiz/<id>/answer` | Assessments |
| GET | `/progress`, `/leaderboard` | Progress and gamification |
| GET | `/library[/<slug>]`, `/search?q=` | Study notes |
| POST | `/translate`, `/tts` | Translation and speech |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Accounts |
| GET/PATCH | `/me` | Profile and settings |
| POST | `/feedback` | Feedback |
| GET | `/admin/overview`, `/admin/students`, `/admin/feedback` | Teacher analytics |
| GET/POST/PUT/DELETE | `/admin/documents[/<slug>]` | Content editor |
| GET/PUT | `/admin/ai`, POST `/admin/ai/test` | NVIDIA key, model and connection test |

---

## Deployment

The `Procfile` runs gunicorn with threads, which streaming answers need:

```
build:  pip install -r requirements.txt && cd frontend && npm ci && npm run build
start:  gunicorn "run:app" --worker-class gthread --threads 8 --timeout 180
```

Set `TATVAX_SECRET_KEY`, `TATVAX_SECURE_COOKIES=1` (on HTTPS) and `TATVAX_BEHIND_PROXY=1` (behind a proxy), and give the server a persistent disk for `instance/`. That folder holds the SQLite database, including an NVIDIA key saved from the console, so keep it private. Rate limits are in-memory, so run a single process, or put a shared limiter in front if you scale out.

---

## Known limitations

- Voice *input* uses the browser's Web Speech API, which works in Chrome and Edge but not Firefox. Read-aloud falls back to server-generated audio when the device has no voice for a language; Odia and Assamese only work on devices that provide their own voice.
- The interface is fully translated into English. The other 12 languages cover the main screens and fall back to English for the rest; review by native speakers is welcome. AI answers are fully in the chosen language.
- Notes mode translates with free public endpoints, which can be rate limited.

---

## License

MIT. See [LICENSE](LICENSE).
