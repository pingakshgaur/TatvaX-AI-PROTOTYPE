from flask import Flask, render_template, request, jsonify, send_file
import os
import traceback
from datetime import datetime

# Import our custom modules
from translation_service import TranslationService
from content_manager import ContentManager
from chatbot_helpers import EnhancedChatbotHelpers

# Create Flask app
app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)

app.config["SECRET_KEY"] = "tatvax-enhanced-secret-key-2025"

# Global instances
translation_service = None
content_manager = None
chatbot_helper = None
conversation_history = []

# Supported languages with native names
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "हिंदी (Hindi)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "te": "తెలుగు (Telugu)",
    "ta": "தமிழ் (Tamil)",
    "gu": "ગુજરાતી (Gujarati)",
    "kn": "ಕನ್ನಡ (Kannada)",
}


def initialize_services():
    """Initialize all services"""
    global translation_service, content_manager, chatbot_helper
    try:
        print("🚀 Initializing Enhanced TatvaX Services...")

        # Initialize translation service
        translation_service = TranslationService()
        print("✅ Translation service initialized")

        # Initialize content manager
        content_manager = ContentManager()
        print("✅ Content manager initialized")

        # Initialize enhanced chatbot helper
        chatbot_helper = EnhancedChatbotHelpers(translation_service, content_manager)
        print("✅ Enhanced chatbot helper initialized")

        return True
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        traceback.print_exc()
        return False


def process_user_input(text, input_type="text", selected_language="en"):
    """Enhanced input processing with multi-language support"""
    try:
        # Detect input language
        detected_lang = translation_service.detect_language(text)
        print(f"🔍 Input language detected: {detected_lang}")

        # Translate to English for processing if needed
        if detected_lang != "en":
            english_query = translation_service.translate_text(text, target_lang="en")
        else:
            english_query = text

        return {
            "original_text": text,
            "original_language": detected_lang,
            "english_query": english_query,
            "selected_language": selected_language,
            "input_type": input_type,
        }
    except Exception as e:
        return {"error": str(e), "input_type": input_type}


def generate_enhanced_response(input_data, chat_mode="subjects"):
    """Generate response based on chat mode (subjects or institutional)"""
    try:
        if "error" in input_data:
            return {"error": input_data["error"], "status": "error"}

        english_query = input_data["english_query"]
        selected_language = input_data["selected_language"]
        original_text = input_data["original_text"]

        print(f"📝 Processing {chat_mode} query: {english_query}")
        print(f"🗣️ Target language: {selected_language}")

        if chat_mode == "institutional":
            # Handle institutional FAQs
            response = chatbot_helper.handle_institutional_query(english_query)
        else:
            # Handle subject-based queries
            subject = input_data.get("subject", "general")
            response = chatbot_helper.handle_subject_query(english_query, subject)

        # Translate response to selected language if needed
        if selected_language != "en":
            translated_response = translation_service.translate_text(
                response, target_lang=selected_language
            )
        else:
            translated_response = response

        # Generate audio if needed
        try:
            audio_file = chatbot_helper.generate_audio(
                translated_response, selected_language
            )
        except Exception as e:
            print(f"⚠️ Audio generation failed: {e}")
            audio_file = None

        # Store conversation
        conversation_entry = {
            "query": original_text,
            "query_language": input_data["original_language"],
            "response": translated_response,
            "response_language": selected_language,
            "chat_mode": chat_mode,
            "timestamp": datetime.now().isoformat(),
        }
        conversation_history.append(conversation_entry)

        return {
            "status": "success",
            "original_query": original_text,
            "response": translated_response,
            "response_language": selected_language,
            "audio_file": audio_file,
            "chat_mode": chat_mode,
        }

    except Exception as e:
        print(f"❌ Response generation error: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# Routes
@app.route("/")
def index():
    """Serve the main interface"""
    try:
        return render_template("index.html", languages=SUPPORTED_LANGUAGES)
    except Exception as e:
        print(f"❌ Error serving index page: {e}")
        return f"Error loading page: {str(e)}", 500


@app.route("/api/chat/text", methods=["POST"])
def chat_text():
    """Handle text input"""
    try:
        if not all([translation_service, content_manager, chatbot_helper]):
            return jsonify({"error": "Services not initialized"}), 500

        data = request.get_json()
        user_input = data.get("message", "")
        chat_mode = data.get("mode", "subjects")  # subjects or institutional
        selected_language = data.get("language", "en")
        subject = data.get("subject", "general")

        if not user_input.strip():
            return jsonify({"error": "Empty message"}), 400

        print(f"💬 Processing {chat_mode} text input: {user_input}")

        # Process input
        input_data = process_user_input(user_input, "text", selected_language)
        input_data["subject"] = subject

        # Generate response
        response = generate_enhanced_response(input_data, chat_mode)

        return jsonify(response)
    except Exception as e:
        error_msg = f"Chat text error: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500


@app.route("/api/chat/voice", methods=["POST"])
def chat_voice():
    """Handle voice input"""
    try:
        if not chatbot_helper:
            return jsonify({"error": "Chatbot not initialized"}), 500

        data = request.get_json()
        chat_mode = data.get("mode", "subjects")
        selected_language = data.get("language", "en")
        subject = data.get("subject", "general")

        print("🎤 Processing voice input...")

        # Get speech input
        speech_text = chatbot_helper.speech_to_text()

        # Process voice input
        input_data = process_user_input(speech_text, "voice", selected_language)
        input_data["subject"] = subject

        # Generate response
        response = generate_enhanced_response(input_data, chat_mode)

        return jsonify(response)
    except Exception as e:
        error_msg = f"Chat voice error: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500


@app.route("/api/subjects")
def get_subjects():
    """Get available subjects"""
    try:
        if not content_manager:
            return jsonify({"error": "Content manager not initialized"}), 500

        subjects = content_manager.get_available_subjects()
        return jsonify({"status": "success", "subjects": subjects})
    except Exception as e:
        print(f"❌ Error getting subjects: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/languages")
def get_languages():
    """Get supported languages"""
    try:
        return jsonify({"status": "success", "languages": SUPPORTED_LANGUAGES})
    except Exception as e:
        print(f"❌ Error getting languages: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/translate", methods=["POST"])
def translate_text():
    """Translate text endpoint"""
    try:
        if not translation_service:
            return jsonify({"error": "Translation service not initialized"}), 500

        data = request.get_json()
        text = data.get("text", "")
        target_lang = data.get("target_language", "en")
        source_lang = data.get("source_language", "auto")

        if not text.strip():
            return jsonify({"error": "Empty text"}), 400

        translated_text = translation_service.translate_text(
            text, target_lang=target_lang, source_lang=source_lang
        )

        return jsonify(
            {
                "status": "success",
                "original_text": text,
                "translated_text": translated_text,
                "target_language": target_lang,
            }
        )
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/<filename>")
def serve_audio(filename):
    """Serve audio files"""
    try:
        audio_path = os.path.join("temp_audio", filename)
        if os.path.exists(audio_path):
            return send_file(audio_path, as_attachment=False, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        print(f"❌ Error serving audio: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/play/<filename>")
def play_audio_file(filename):
    """Play specific audio file"""
    try:
        if not chatbot_helper:
            return jsonify({"error": "Chatbot not initialized"}), 500

        audio_path = os.path.join("temp_audio", filename)
        if chatbot_helper.play_audio_file(audio_path):
            return jsonify({"status": "success", "message": "Audio playing"})
        else:
            return jsonify({"error": "Failed to play audio"}), 500
    except Exception as e:
        print(f"❌ Error playing audio: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/stop", methods=["POST"])
def stop_audio():
    """Stop currently playing audio"""
    try:
        if not chatbot_helper:
            return jsonify({"error": "Chatbot not initialized"}), 500

        if chatbot_helper.stop_audio():
            return jsonify({"status": "success", "message": "Audio stopped"})
        else:
            return jsonify({"error": "Failed to stop audio"}), 500
    except Exception as e:
        print(f"❌ Error stopping audio: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Handle feedback submission"""
    try:
        data = request.get_json()

        if not data.get("message"):
            return (
                jsonify({"status": "error", "message": "Feedback message is required"}),
                400,
            )

        feedback_entry = {
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "rating": data.get("rating", "Not rated"),
            "name": data.get("name", "Anonymous"),
            "email": data.get("email", "Not provided"),
            "message": data.get("message", ""),
            "current_page": data.get("currentPage", "Unknown"),
            "user_agent": data.get("userAgent", "Unknown"),
        }

        static_dir = "static"
        os.makedirs(static_dir, exist_ok=True)

        feedback_text = f"""
{'='*60}
ENHANCED TATVAX FEEDBACK SUBMISSION
{'='*60}
Timestamp: {feedback_entry['timestamp']}
Rating: {feedback_entry['rating']}/5 stars
Name: {feedback_entry['name']}
Email: {feedback_entry['email']}
Current Page: {feedback_entry['current_page']}

Feedback Message:
{feedback_entry['message']}

{'='*60}

"""

        feedback_file = os.path.join(static_dir, "tatvax_feedback.txt")

        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(feedback_text)

        print(
            f"✅ Feedback saved: {feedback_entry['name']} - {feedback_entry['rating']} stars"
        )

        return jsonify(
            {
                "status": "success",
                "message": "Feedback submitted successfully!",
                "feedback_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            }
        )

    except Exception as e:
        print(f"❌ Feedback submission error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to save feedback. Please try again.",
                }
            ),
            500,
        )


@app.route("/api/clear", methods=["POST"])
def clear_chat():
    """Clear conversation history"""
    try:
        global conversation_history
        conversation_history = []

        # Clean up temp audio files
        temp_audio_dir = "temp_audio"
        if os.path.exists(temp_audio_dir):
            for file in os.listdir(temp_audio_dir):
                try:
                    os.remove(os.path.join(temp_audio_dir, file))
                except:
                    pass

        print("🧹 Chat history and temp files cleared")
        return jsonify({"status": "success", "message": "Chat history cleared"})
    except Exception as e:
        print(f"❌ Error clearing chat: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def get_status():
    """Enhanced system status"""
    try:
        status = {
            "status": "success",
            "services_initialized": {
                "translation_service": translation_service is not None,
                "content_manager": content_manager is not None,
                "chatbot_helper": chatbot_helper is not None,
            },
            "conversation_count": len(conversation_history),
            "server_time": datetime.now().isoformat(),
            "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
            "available_subjects": (
                content_manager.get_available_subjects() if content_manager else []
            ),
            "audio_playing": (
                chatbot_helper.is_audio_playing() if chatbot_helper else False
            ),
            "version": "3.0.0 - Enhanced Edition",
        }
        return jsonify(status)
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    # Create necessary directories
    directories = [
        "content_library",
        "content_library/subjects",
        "content_library/institutional",
        "static",
        "templates",
        "temp_audio",
    ]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")
        except Exception as e:
            print(f"❌ Error creating directory {directory}: {e}")

    # Initialize services
    if not initialize_services():
        print("❌ Failed to initialize services. Please check your configuration.")
        exit(1)

    print("🌟 Starting Enhanced TatvaX Server...")
    print("📚 New Features:")
    print("├── 8 Language Support :-")
    print("|\t└── Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, English, Kannada.")
    print("├── Institutional FAQs Chat Mode")
    print("├── Subject-based Learning Mode")
    print("├── Enhanced Translation with Multiple APIs")
    print("├── Modern UI with New Color Scheme")
    print("└── Voice Input/Output in All Languages")
    print("\n\n\n🌐 Access TatvaX at: http://localhost:5000\n\n")

    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        traceback.print_exc()
