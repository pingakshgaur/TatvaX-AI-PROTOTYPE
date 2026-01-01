# <ins>TatvaX AI [PROTOTYPE] - ReadMe</ins>
TatvaX is a groundbreaking educational AI platform that democratises learning by breaking language barriers. Built with cutting-edge AI technology, TatvaX delivers personalized educational content across 8 Indian languages (Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Kannada, and English), making quality education accessible to millions.

<div align="center">

![TatvaX Banner](https://img.shields.io/badge/TatvaX-Prototype%20v1.0-blue?style=for-the-badge&logo=python)
![Languages](https://img.shields.io/badge/Languages-8%20Supported-green?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI-Powered-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Prototype-yellow?style=for-the-badge)

**Breaking language barriers in education with AI**

[🚀 Features](#-features) • [📥 Installation](#-installation) • [🎯 Usage](#-usage) • [🔧 Tech Stack](#-tech-stack) • [🤝 Contributing](#-contributing)

</div>

---

## 🎥 **Watch TatvaX in Action**

[![Video Title](https://img.youtube.com/vi/VIDEO_ID/0.jpg)](https://youtu.be/hqo_TAZh0ls)

---

## ⚠️ **IMPORTANT NOTICE - PROTOTYPE VERSION**

> **This repository contains a PROTOTYPE implementation of TatvaX.**
> 
> This is a **proof-of-concept** demonstrating the core functionality and vision of the TatvaX platform. The final product will include enhanced features, scalability improvements, production-grade security, cloud infrastructure, and significantly expanded educational content.
>
> **This prototype serves as:**
> - 🎯 Demonstration of core concept and functionality
> - 🧪 Testing ground for multilingual AI education
> - 📊 Foundation for gathering feedback and insights
> - 🚀 Starting point for the full-scale production version

---

## 📖 **Table of Contents**

- [About TatvaX](#-about-tatvax)
- [Features](#-features)
- [Why TatvaX is Revolutionary](#-why-tatvax-is-revolutionary)
- [Installation](#-installation)
- [Usage](#-usage)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)
- [Team](#-team)
- [Acknowledgements](#-acknowledgments)
- [Project Stats](#-project-stats)
- [Quick Links](#-quick-links)

---

## 🎓 **About TatvaX**

**TatvaX** is a revolutionary AI-powered educational platform that breaks language barriers to make quality education accessible to everyone. Built with a vision to democratize learning, TatvaX delivers personalized educational content in **8 Indian languages**, ensuring that language is never a barrier to knowledge.

### **Our Vision** 🌍

To create an inclusive learning ecosystem where every student can access quality education in their native language, powered by advanced AI technology.

### **Our Mission** 🎯

- Make quality education accessible to all linguistic communities
- Leverage AI to provide personalized, context-aware learning experiences
- Bridge the digital divide with voice-first learning capabilities
- Empower students to learn in the language they're most comfortable with

---

## ✨ **Features**

### 🎓 **Dual Learning Modes**

#### **1. Subject Learning Mode**
Interactive learning across 4 core subjects with AI-powered responses:
- 📐 **Mathematics**: Concepts, problem-solving, formulas
- 🔬 **Science**: Physics, Chemistry, Biology explanations
- 📚 **English**: Grammar, literature, writing skills
- 🌍 **Social Studies**: History, geography, civics

#### **2. Institutional FAQ Mode**
Comprehensive school information system covering:
- 🏫 Admission procedures and requirements
- 💰 Fee structure and payment information
- 📅 Academic calendar and exam schedules
- 📋 School policies and guidelines
- 🎓 Scholarship and financial aid information

### 🌐 **Multilingual AI Engine**

**8 Supported Languages:**
- 🇮🇳 **Hindi** (हिंदी)
- 🇮🇳 **Bengali** (বাংলা)
- 🇮🇳 **Marathi** (मराठी)
- 🇮🇳 **Telugu** (తెలుగు)
- 🇮🇳 **Tamil** (தமிழ்)
- 🇮🇳 **Gujarati** (ગુજરાતી)
- 🇮🇳 **Kannada** (ಕನ್ನಡ)
- 🇺🇸 **English**

**Smart Translation System:**
- Multiple translation API fallback (Google Free, MyMemory, LibreTranslate)
- Auto-detection of input language
- Context-aware translations
- Real-time processing

### 🎙️ **Voice-First Learning**

- **Voice Input**: Speak your questions in any supported language
- **Voice Output**: Listen to responses with text-to-speech
- **Hands-Free Learning**: Perfect for accessibility
- **Natural Language Processing**: Understands conversational queries

### 🎨 **Modern User Experience**

- **Beautiful Interface**: Clean, modern design with smooth animations
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Code Block Display**: Formatted output with copy functionality
- **Intuitive Navigation**: Easy-to-use for all age groups
- **Dark Mode Ready**: Easy on the eyes

### 🔧 **Advanced Technical Features**

- **Content Management System**: Extensive educational content library
- **AI Response Generation**: Context-aware, intelligent responses
- **Audio Processing**: High-quality TTS and speech recognition
- **Fallback Systems**: Multiple API fallback for reliability
- **Feedback System**: Built-in user feedback collection
- **Translation Mode**: Quick translate between any languages

---

## 🚀 **Why TatvaX is Revolutionary**

### **1. True Linguistic Inclusion** 🌍
Unlike platforms that simply translate content, TatvaX understands cultural context and learning patterns specific to each language, making education truly accessible.

### **2. Voice-First Approach** 🎙️
TatvaX enables hands-free learning through comprehensive voice input/output, making education accessible for students with diverse learning styles and abilities.

### **3. Dual-Mode Intelligence** 🧠
Seamlessly switches between subject learning and institutional FAQs, providing a complete educational ecosystem in one platform.

### **4. Robust Architecture** 🏗️
Multi-API fallback system ensures the platform works even when primary services are down, guaranteeing consistent access to education.

### **5. AI-Powered Personalisation** 🤖
Advanced NLP algorithms provide context-aware responses tailored to each student's language and learning level.

### **6. Accessibility First** ♿
Voice input/output, clean interface, and multilingual support make TatvaX accessible to students with various needs and backgrounds.

---

## 📥 **Installation**

### **Prerequisites**

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection (for translation APIs)
- Microphone (optional, for voice input)
- Speakers/Headphones (optional, for audio output)

### **Quick Start** ⚡

1. **Clone the Repository**
```
git clone https://github.com/your-username/tatvax-ai-prototype.git
cd tatvax-ai-prototype
```

2. **Create Virtual Environment**

#### Windows
```
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux
```
python3 -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```
pip install -r requirements.txt
```

4. **Download NLTK Data**
```
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

5. **Run TatvaX**
```
python app.py
```

6. **Access the Platform**
```
Open browser → http://localhost:5000
```

That's it! TatvaX is now running locally. 🎉

---

## 🎯 **Usage**

### **Getting Started** 🚦

#### **Step 1: Choose Your Mode**
After launching TatvaX, you'll see two learning modes:

- **📚 Subject Learning**: Get AI-powered help with Mathematics, Science, English, and Social Studies
- **🏫 Institutional Assistant**: Ask questions about school policies, fees, schedules, and more

#### **Step 2: Select Your Language**
Choose from 8 supported languages in the dropdown menu. The entire interface adapts to your selection.

#### **Step 3: Start Learning**
- **Type** your question in the text box, OR
- **Click the microphone** 🎙️ and speak your question
- Get instant AI-powered responses in your chosen language
- **Click audio button** 🔊 to hear the response

### **Example Queries** 💬

#### **Mathematics** 📐
```

"Explain Pythagoras theorem"
"How to solve quadratic equations?"
"What is the formula for area of circle?"
"Teach me trigonometry basics"

```

#### **Science** 🔬
```

"Explain photosynthesis process"
"What are Newton's laws of motion?"
"How does the digestive system work?"
"Tell me about solar system"

```

#### **English** 📖
```

"What are parts of speech?"
"How to write a good essay?"
"Explain active and passive voice"
"Give me grammar tips"

```

#### **Social Studies** 🌍
```

"Tell me about Indian independence"
"What is democracy?"
"Explain fundamental rights"
"History of Mughal empire"

```

#### **Institutional FAQs** 🏫
```

"What are admission requirements?"
"When are exam dates?"
"How much is school fee?"
"What is school timing?"
"How to apply for scholarship?"

```

### **Pro Tips** 💡

✨ **Voice Input**: Works best in quiet environments  
✨ **Language Mix**: Can understand code-switched queries  
✨ **Quick Translate**: Press `Ctrl+K` for instant translation  
✨ **Copy Response**: Click copy button on any response  
✨ **Audio Speed**: Browser controls audio playback speed  

---

## 🔧 **Tech Stack**

### **Frontend** 💻
| Technology | Purpose |
|------------|---------|
| **HTML5** | Semantic structure |
| **CSS3** | Modern styling with animations |
| **JavaScript ES6+** | Interactive functionality |
| **Responsive Design** | Mobile-first approach |

### **Backend** ⚙️
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Core language |
| **Flask** | 2.3+ | Web framework |
| **NLTK** | 3.8+ | NLP processing |
| **Sumy** | 0.11+ | Text summarization |

### **AI & Translation** 🤖
- **Google Translate API** (Primary)
- **MyMemory API** (Fallback)
- **LibreTranslate** (Secondary fallback)
- **Custom NLP Engine** (Context awareness)

### **Audio Processing** 🎙️
- **gTTS**: Text-to-speech generation
- **SpeechRecognition**: Voice input
- **pygame**: Audio playback
- **PyAudio**: Audio capture

### **Key Dependencies** 📦
```
Flask==2.3.0
nltk==3.8.1
sumy==0.11.0
gtts==2.3.2
pygame==2.5.2
SpeechRecognition==3.10.0
PyAudio==0.2.13
requests==2.31.0
```

---

## 🏗️ **Architecture**

### **System Overview**

```
┌────────────────────────────────────────────────┐
│         User Interface (HTML/CSS/JS)           │
│   -  Responsive Design  -  Voice Controls      │
│   -  8 Language Support -  Real-time Updates   │
└───────────────────────┬────────────────────────┘
                        │
┌───────────────────────▼────────────────────────┐
│           Flask Application Layer              │
│   -  Routing               -  API Endpoints    │
│   -  Session Management                        │
└───────────────────────┬────────────────────────┘
                        │
           ┌────────────┼────────────┐
           |            │            │
     ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
     │Translation│ │Content  │ │  Chatbot  │
     │  Service  │ │ Manager │ │  Helpers  │
     │ Multi-API │ │ Library │ │  AI/NLP   │
     └───────────┘ └─────────┘ └───────────┘
           │            │            │
           └────────────┼────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│        External Services \& Resources           │
│   -  Translation APIs    -  Audio Processing    │
│   -  Content Database    -  Temporary Storage   │
└─────────────────────────────────────────────────┘
```

### **Request Flow**

```

User Input
    ↓
Language Detection
    ↓
Translation (if needed)
    ↓
Content Retrieval
    ↓
AI Processing
    ↓
Response Generation
    ↓
Translation to Target Language
    ↓
Audio Generation (optional)
    ↓
Response Delivery to Frontend

```

### **Key Components**

#### **1. Translation Service** 🌍
- Multi-API architecture with automatic fallback
- Supports 8 languages with high accuracy
- Caching for improved performance

#### **2. Content Manager** 📚
- Organized subject-wise content library
- Keyword-based content retrieval
- Institutional FAQ database

#### **3. Chatbot Helpers** 🤖
- NLP-powered query understanding
- Context-aware response generation
- Multi-language support

#### **4. Audio Processor** 🎙️
- Real-time speech recognition
- High-quality text-to-speech
- Temporary file management

---

## 📡 **API Documentation**

### **Base URL**
```

http://localhost:5000/api

```

### **Endpoints**

#### **1. Text Chat**
```

POST /api/chat/text
Content-Type: application/json

```

**Request Body:**
```

{
"message": "Your question here",
"mode": "subjects",
"language": "en",
"subject": "mathematics"
}

```

**Response:**
```

{
"status": "success",
"response": "AI generated response text",
"audio_file": "response_12345.mp3"
}

```

**Parameters:**
| Field | Type | Required | Options |
|-------|------|----------|---------|
| `message` | string | ✅ | User query |
| `mode` | string | ✅ | `subjects`, `institutional` |
| `language` | string | ✅ | `en`, `hi`, `bn`, `mr`, `te`, `ta`, `gu`, `kn` |
| `subject` | string | ⚠️ | Required for subjects mode |

---

#### **2. Voice Chat**
```

POST /api/chat/voice
Content-Type: application/json

```

**Request Body:**
```

{
"mode": "subjects",
"language": "hi",
"subject": "science"
}

```

**Response:**
```

{
"status": "success",
"original_query": "Recognized user speech",
"response": "AI response text",
"audio_file": "response_67890.mp3"
}

```

---

#### **3. Translation**
```

POST /api/translate
Content-Type: application/json

```

**Request Body:**
```

{
"text": "Text to translate",
"source_language": "en",
"target_language": "hi"
}

```

**Response:**
```

{
"status": "success",
"translated_text": "अनुवादित पाठ"
}

```

---

#### **4. System Status**
```

GET /api/status

```

**Response:**
```

{
"status": "success",
"subjects": {
"mathematics": {...},
"science": {...},
"english": {...},
"social_studies": {...}
},
"supported_languages": {
"en": "English",
"hi": "Hindi",
...
}
}

```

---

#### **5. Feedback**
```

POST /api/feedback
Content-Type: application/json

```

**Request Body:**
```

{
"rating": 5,
"name": "User Name",
"message": "Feedback message"
}

```

**Response:**
```

{
"status": "success",
"message": "Feedback saved successfully"
}

```

---

## 📁 **Project Structure**

```

TatvaX-AI-Prototype/
│
├── 📄 app.py                       # Main Flask application
├── 📄 translation_service.py       # Multi-API translation
├── 📄 content_manager.py           # Content library manager
├── 📄 chatbot_helpers.py           # AI/NLP processing
├── 📄 requirements.txtt            # Python dependencies
├── 📄 README.md                    # Documentation
│
├── 📂 static/
│   ├── 📄 style.css                # UI styling
│   ├── 📄 script.js                # Frontend logic
│
├── 📂 templates/
│   └── 📄 index.html               # Main interface
│
├── 📂 content_library/
│   ├── 📂 subjects/
│   │   ├── 📄 mathematics-content.txt
│   │   ├── 📄 science-content.txt
│   │   ├── 📄 english-content.txt
│   │   └── 📄 social-studies-content.txt
│   │
│   └── 📂 institutional/
│       └── 📄 faq_responses.txt
│
└── 📂 temp_audio/                 # Temporary audio storage

```

---

## 🗺️ **Roadmap**

### **✅ Current Version: Prototype v1.0**
- 8-language multilingual support
- Dual learning modes (Subject + Institutional)
- Voice input/output functionality
- Modern UI with code-block display
- Multi-API fallback system
- Comprehensive content library

### **🎯 Upcoming: v1.5 (Q2 2025)**
- [ ] GPT/Gemini AI integration
- [ ] User authentication & profiles
- [ ] Learning progress tracking
- [ ] Multiple UI themes
- [ ] PWA support for offline access
- [ ] Enhanced voice recognition accuracy

### **🚀 Future: v2.0 (Q4 2025)**
- [ ] 15+ language support
- [ ] Gamification (points, badges, leaderboards)
- [ ] Interactive quizzes & assessments
- [ ] Video learning modules
- [ ] Real-time collaboration features
- [ ] Advanced analytics dashboard

### **🌟 Vision: v3.0 (2026)**
- [ ] Native mobile apps (iOS & Android)
- [ ] AR/VR learning experiences
- [ ] AI tutor personalization
- [ ] Blockchain-based certificates
- [ ] Global content marketplace
- [ ] Teacher dashboard & CMS

---

## 🤝 **Contributing**

We welcome contributions from developers, educators, linguists, and students!

### **How to Contribute**

1. **🍴 Fork** the repository
2. **🔧 Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **💻 Commit** changes (`git commit -m 'Add amazing feature'`)
4. **📤 Push** to branch (`git push origin feature/amazing-feature`)
5. **🔀 Open** a Pull Request

### **Contribution Areas**

| Area | What We Need |
|------|--------------|
| 🌍 **Languages** | Add new language support, improve translations |
| 📚 **Content** | Expand educational content, add subjects |
| 🎨 **UI/UX** | Improve design, add themes, enhance accessibility |
| 🤖 **AI/ML** | Enhance NLP, improve response quality |
| 🐛 **Bug Fixes** | Report and fix bugs |
| 📖 **Documentation** | Improve guides, add tutorials |
| 🔧 **Features** | Implement new functionality |

### **Code Style Guidelines**

- **Python**: Follow PEP 8 standards
- **JavaScript**: Use ES6+ features, follow ESLint
- **HTML/CSS**: Semantic markup, BEM methodology
- **Commits**: Clear, descriptive messages

---

## 🔍 **Troubleshooting**

### **Common Issues & Solutions**

#### **❌ PyAudio Installation Fails**

**Windows:**
```

pip install pipwin
pipwin install pyaudio

```

**macOS:**
```

brew install portaudio
pip install pyaudio

```

**Linux:**
```

sudo apt-get install portaudio19-dev
pip install pyaudio

```

---

#### **❌ NLTK Data Missing**

```

import nltk
nltk.download('punkt')
nltk.download('stopwords')

```

---

#### **❌ Translation Not Working**

**Check:**
- ✅ Internet connection is stable
- ✅ No firewall blocking API requests
- ✅ API rate limits not exceeded
- ✅ Try different language pairs

**System automatically falls back to alternate APIs**

---

#### **❌ Voice Input Not Working**

**Solutions:**
- ✅ Use Chrome or Edge (recommended)
- ✅ Grant microphone permissions
- ✅ Check microphone is not in use
- ✅ Speak clearly in quiet environment
- ✅ Ensure microphone is properly connected

---

#### **❌ Audio Playback Issues**

**Solutions:**
- ✅ Check speaker/headphone connection
- ✅ Verify browser audio permissions
- ✅ Try different browser
- ✅ Clear `temp_audio` folder
- ✅ Restart application

---

#### **❌ Slow Performance**

**Optimize:**
- ✅ Check internet speed
- ✅ Clear browser cache
- ✅ Close unnecessary tabs/applications
- ✅ Delete old audio files from `temp_audio/`
- ✅ Ensure sufficient RAM available

---

### **Getting Help** 💬

**Before Creating an Issue:**
1. Check existing [GitHub Issues](https://github.com/your-username/TatvaX-AI-Prototype/issues)
2. Review troubleshooting section
3. Search documentation

**When Creating an Issue:**
- Describe the problem clearly
- Include steps to reproduce
- Attach error messages/screenshots
- Specify system information (OS, Python version, browser)

---

## 📄 **License**

This project is licensed under the **MIT License**.



MIT License

Copyright (c) 2025 Team Cortex Coders (Pingaksh Gaur)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software...


See [LICENSE](LICENSE) file for full details.

---

## 👥 **Team**

### **Team Cortex Coders 🧠**

**Empowering education through AI innovation**

**Project Lead & Developer**
- Vision, strategy, and architecture
- Full-stack development
- AI/ML integration

**Open for Contributors!**
Join our mission to make education accessible to everyone.

### **Contact & Community**
- **LinkedIn**: _[@PingakshGaur](https://linkedin.com/in/pingakshgaur)_
- **Issues**: _[Report Bug](https://github.com/your-username/TatvaX-Prototype/issues/new)_
- **Feature Requests**: _[Request Feature](https://github.com/your-username/tatvax-ai-prototype/issues/new?labels=enhancement)_

---

## 🙏 **Acknowledgments**

Special thanks to:

- **Translation APIs**: Google Translate, MyMemory, LibreTranslate
- **Audio Libraries**: gTTS, pygame, SpeechRecognition, PyAudio
- **NLP Tools**: NLTK, Sumy
- **Students & Educators**: For feedback and inspiration

---

## 📊 **Project Stats**

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-green?style=flat-square&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow?style=flat-square&logo=javascript&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-Latest-orange?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-Latest-blue?style=flat-square&logo=css3&logoColor=white)

![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)
![Version](https://img.shields.io/badge/Version-Prototype%20v1.0-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Contributors](https://img.shields.io/badge/Contributors-Welcome-orange?style=flat-square)

</div>

---

## 🔗 **Quick Links**

| Resource | Link |
|----------|------|
| 🚀 **Getting Started** | [Installation Guide](#-installation) |
| 📖 **Documentation** | [Full Docs](#-api-documentation) |
| 💬 **Report Issue** | [GitHub Issues](https://github.com/your-username/tatvax-ai-prototype/issues) |
| 🤝 **Contribute** | [Contributing Guide](#-contributing) |
| 🗺️ **Roadmap** | [Future Plans](#-roadmap) |

---

<div align="center">

## 🌟 **Made with ❤️ by Team Cortex Coders** 🌟

*Breaking language barriers, building futures*

**If TatvaX inspired you or helped in any way, please ⭐ star this repository!**

[![Star on GitHub](https://img.shields.io/github/stars/your-username/TatvaX-Prototype?style=social)](https://github.com/your-username/TatvaX-Prototype)
[![Fork on GitHub](https://img.shields.io/github/forks/your-username/TatvaX-Prototype?style=social)](https://github.com/your-username/TatvaX-Prototype/fork)

</div>

---

> **"Education is the most powerful weapon which you can use to change the world."**  
> — Nelson Mandela

> **"The beautiful thing about learning is that no one can take it away from you."**  
> — B.B. King

---

<div align="center">

### **© 2025 Team Cortex Coders. All rights reserved.**

*This is a prototype version. The final product will include enhanced features, scalability, and production-grade quality.*

**⚠️ PROTOTYPE - For demonstration and feedback purposes**

</div>
