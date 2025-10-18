import requests
import json
import re
from typing import Dict, List, Optional
import time


class TranslationService:
    """Enhanced Translation Service with Improved TTS for Natural Pronunciation"""

    def __init__(self):
        print("🔄 Initializing Enhanced Translation Service...")

        # Language mappings
        self.language_codes = {
            "en": "English",
            "hi": "Hindi",
            "bn": "Bengali",
            "mr": "Marathi",
            "te": "Telugu",
            "ta": "Tamil",
            "gu": "Gujarati",
            "kn": "Kannada",
        }

        # Translation APIs configuration (in priority order)
        self.apis = {
            "google_free": {
                "url": "https://translate.googleapis.com/translate_a/single",
                "active": True,
                "priority": 1,
                "max_chars": 5000,
            },
            "mymemory": {
                "url": "https://api.mymemory.translated.net/get",
                "active": True,
                "priority": 2,
                "max_chars": 1000,
            },
            "libretranslate": {
                "url": "https://translate.disroot.org/translate",
                "active": True,
                "priority": 3,
                "max_chars": 2000,
            },
        }

        # Enhanced fallback dictionary for educational terms
        self.fallback_dict = self.load_comprehensive_dictionary()

        # TTS language mapping for better pronunciation
        self.tts_language_mapping = {
            "en": "en",
            "hi": "hi",
            "bn": "bn",
            "mr": "hi",  # Use Hindi TTS for Marathi (similar script)
            "te": "te",
            "ta": "ta",
            "gu": "gu",
            "kn": "kn",
        }

        # Common pronunciation fixes for each language
        self.pronunciation_fixes = self.load_pronunciation_fixes()

        print("✅ Enhanced Translation Service initialized")
        print(f"📚 Loaded {len(self.fallback_dict)} language pairs")
        print(f"🎙️ TTS support for {len(self.tts_language_mapping)} languages")

    def load_comprehensive_dictionary(self) -> Dict[str, Dict[str, str]]:
        """Load comprehensive educational vocabulary dictionary"""
        return {
            "en_to_hi": {
                # Educational terms
                "mathematics": "गणित",
                "science": "विज्ञान",
                "english": "अंग्रेजी",
                "social studies": "सामाजिक अध्ययन",
                "physics": "भौतिकी",
                "chemistry": "रसायन विज्ञान",
                "biology": "जीव विज्ञान",
                "history": "इतिहास",
                "geography": "भूगोल",
                "literature": "साहित्य",
                "grammar": "व्याकरण",
                "vocabulary": "शब्दावली",
                "chapter": "अध्याय",
                "lesson": "पाठ",
                "exercise": "अभ्यास",
                "example": "उदाहरण",
                "question": "प्रश्न",
                "answer": "उत्तर",
                "solution": "समाधान",
                # Numbers and math
                "number": "संख्या",
                "addition": "जोड़",
                "subtraction": "घटाव",
                "multiplication": "गुणा",
                "division": "भाग",
                "fraction": "भिन्न",
                "decimal": "दशमलव",
                "percentage": "प्रतिशत",
                "equation": "समीकरण",
                "formula": "सूत्र",
                "calculation": "गणना",
                # Institutional terms
                "examination": "परीक्षा",
                "test": "परीक्षण",
                "syllabus": "पाठ्यक्रम",
                "curriculum": "पाठ्यक्रम",
                "timetable": "समय सारणी",
                "schedule": "कार्यक्रम",
                "admission": "प्रवेश",
                "fee": "शुल्क",
                "fees": "शुल्क",
                "scholarship": "छात्रवृत्ति",
                "library": "पुस्तकालय",
                "laboratory": "प्रयोगशाला",
                "principal": "प्राचार्य",
                "teacher": "शिक्षक",
                "student": "छात्र",
                "classroom": "कक्षा",
                "homework": "गृहकार्य",
                "assignment": "असाइनमेंट",
                "project": "परियोजना",
                "result": "परिणाम",
                "marks": "अंक",
                "grade": "श्रेणी",
                "certificate": "प्रमाण पत्र",
                "diploma": "डिप्लोमा",
                # Common phrases and sentences
                "hello": "नमस्ते",
                "good morning": "सुप्रभात",
                "good afternoon": "नमस्कार",
                "good evening": "शुभ संध्या",
                "good night": "शुभ रात्रि",
                "thank you": "धन्यवाद",
                "please": "कृपया",
                "excuse me": "माफ करें",
                "sorry": "माफ करें",
                "help": "मदद",
                "understand": "समझना",
                "explain": "समझाना",
                "learn": "सीखना",
                "study": "अध्ययन",
                "practice": "अभ्यास करना",
                "repeat": "दोहराना",
                "remember": "याद रखना",
                "forget": "भूलना",
                "know": "जानना",
                # Time and calendar
                "today": "आज",
                "tomorrow": "कल",
                "yesterday": "कल",
                "morning": "सुबह",
                "afternoon": "दोपहर",
                "evening": "शाम",
                "night": "रात",
                "week": "सप्ताह",
                "month": "महीना",
                "year": "साल",
                "day": "दिन",
                "time": "समय",
                "hour": "घंटा",
                "minute": "मिनट",
                # Basic verbs in proper forms
                "is": "है",
                "are": "हैं",
                "was": "था",
                "were": "थे",
                "will be": "होगा",
                "have": "है",
                "has": "है",
                "had": "था",
                "do": "करना",
                "does": "करता है",
                "did": "किया",
                "can": "सकना",
                "will": "होगा",
                "would": "होगा",
                "should": "चाहिए",
                "must": "जरूर",
                # Common adjectives
                "good": "अच्छा",
                "bad": "बुरा",
                "big": "बड़ा",
                "small": "छोटा",
                "new": "नया",
                "old": "पुराना",
                "easy": "आसान",
                "difficult": "कठिन",
                "important": "महत्वपूर्ण",
                "useful": "उपयोगी",
                "interesting": "दिलचस्प",
                "beautiful": "सुंदर",
                # Educational verbs
                "read": "पढ़ना",
                "write": "लिखना",
                "listen": "सुनना",
                "speak": "बोलना",
                "think": "सोचना",
                "solve": "हल करना",
                "calculate": "गणना करना",
                "measure": "मापना",
                "observe": "देखना",
                "experiment": "प्रयोग करना",
            },
            "hi_to_en": {
                # Reverse mappings for Hindi to English
                "गणित": "mathematics",
                "विज्ञान": "science",
                "अंग्रेजी": "english",
                "सामाजिक अध्ययन": "social studies",
                "परीक्षा": "examination",
                "शिक्षक": "teacher",
                "छात्र": "student",
                "प्रश्न": "question",
                "उत्तर": "answer",
                "अध्ययन": "study",
                "सीखना": "learn",
                "समझना": "understand",
                "पढ़ना": "read",
                "लिखना": "write",
                "गणना": "calculation",
                "समाधान": "solution",
                "उदाहरण": "example",
                "अभ्यास": "practice",
                "याद रखना": "remember",
                "समझाना": "explain",
                "दोहराना": "repeat",
                "कठिन": "difficult",
                "आसान": "easy",
                "महत्वपूर्ण": "important",
                "अच्छा": "good",
                "बुरा": "bad",
                "नया": "new",
                "पुराना": "old",
            },
        }

    def load_pronunciation_fixes(self) -> Dict[str, Dict[str, str]]:
        """Load pronunciation fixes for better TTS output"""
        return {
            "hi": {
                # Common TTS pronunciation issues in Hindi
                "और": "और ",  # Add space for better pronunciation
                "है।": "है।",  # Proper sentence ending
                "हैं।": "हैं।",
                "था।": "था।",
                "थे।": "थे।",
                "करना": "करना",
                "होना": "होना",
                "जाना": "जाना",
                "आना": "आना",
                "देना": "देना",
                "लेना": "लेना",
                "कहना": "कहना",
                "सुनना": "सुनना",
                "देखना": "देखना",
                "पढ़ना": "पढ़ना",
                "लिखना": "लिखना",
                "समझना": "समझना",
                # Fix common word combinations
                "के लिए": "के लिए",
                "में से": "में से",
                "की तरह": "की तरह",
                "के साथ": "के साथ",
                "के बाद": "के बाद",
                "से पहले": "से पहले",
                # Numbers pronunciation
                "एक": "एक",
                "दो": "दो",
                "तीन": "तीन",
                "चार": "चार",
                "पांच": "पाँच",
                "छह": "छह",
                "सात": "सात",
                "आठ": "आठ",
                "नौ": "नौ",
                "दस": "दस",
            }
        }

    def detect_language(self, text: str) -> str:
        """Enhanced language detection with better script recognition"""
        try:
            if not text or not text.strip():
                return "en"

            # Character counting for different scripts
            script_counts = {
                "devanagari": sum(
                    1 for char in text if "\u0900" <= char <= "\u097f"
                ),  # Hindi, Marathi
                "bengali": sum(1 for char in text if "\u0980" <= char <= "\u09ff"),
                "tamil": sum(1 for char in text if "\u0b80" <= char <= "\u0bff"),
                "telugu": sum(1 for char in text if "\u0c00" <= char <= "\u0c7f"),
                "gujarati": sum(1 for char in text if "\u0a80" <= char <= "\u0aff"),
                "kannada": sum(1 for char in text if "\u0c80" <= char <= "\u0cff"),
            }

            total_chars = len(text.replace(" ", ""))
            if total_chars == 0:
                return "en"

            # Find script with highest percentage
            max_script = max(script_counts, key=script_counts.get)
            max_percentage = script_counts[max_script] / total_chars

            # Language detection based on script
            if max_percentage > 0.15:
                script_to_language = {
                    "devanagari": "hi",  # Default to Hindi for Devanagari
                    "bengali": "bn",
                    "tamil": "ta",
                    "telugu": "te",
                    "gujarati": "gu",
                    "kannada": "kn",
                }

                detected_lang = script_to_language[max_script]

                # Special handling for Marathi (uses Devanagari like Hindi)
                if max_script == "devanagari":
                    marathi_indicators = [
                        "आहे",
                        "माझे",
                        "तुझे",
                        "काय",
                        "कसे",
                        "कुठे",
                        "केव्हा",
                        "कोण",
                    ]
                    if any(word in text for word in marathi_indicators):
                        detected_lang = "mr"

                print(
                    f"🔍 Language detected: {detected_lang} ({max_percentage:.1%} script chars)"
                )
                return detected_lang

            print(f"🔍 Language detected: English (default)")
            return "en"

        except Exception as e:
            print(f"❌ Language detection error: {e}")
            return "en"

    def translate_text(
        self, text: str, target_lang: str = "en", source_lang: str = "auto"
    ) -> str:
        """Enhanced translation with better error handling and quality"""
        try:
            if not text or not text.strip():
                return text

            # Detect source language if auto
            if source_lang == "auto":
                source_lang = self.detect_language(text)

            # Skip translation if source and target are the same
            if source_lang == target_lang:
                return text

            print(f"🔄 Translating from {source_lang} to {target_lang}: {text[:50]}...")

            # Clean and prepare text for translation
            clean_text = self.clean_text_for_translation(text)

            # Try each API in priority order
            for api_name, api_config in sorted(
                self.apis.items(), key=lambda x: x[1]["priority"]
            ):
                if not api_config["active"]:
                    continue

                # Skip if text is too long for this API
                if len(clean_text) > api_config["max_chars"]:
                    continue

                try:
                    if api_name == "google_free":
                        result = self._translate_google_free(
                            clean_text, source_lang, target_lang
                        )
                    elif api_name == "mymemory":
                        result = self._translate_mymemory(
                            clean_text, source_lang, target_lang
                        )
                    elif api_name == "libretranslate":
                        result = self._translate_libretranslate(
                            clean_text, source_lang, target_lang
                        )
                    else:
                        continue

                    if (
                        result
                        and result.strip()
                        and self.validate_translation_quality(
                            clean_text, result, source_lang, target_lang
                        )
                    ):
                        # Post-process the translation
                        processed_result = self.post_process_translation(
                            result, target_lang, source_lang
                        )
                        print(f"✅ Translation successful via {api_name}")
                        return processed_result

                except Exception as e:
                    print(f"⚠️ {api_name} failed: {e}")
                    continue

            # Fallback to dictionary
            print("🔄 Using fallback dictionary...")
            return self._translate_fallback(clean_text, source_lang, target_lang)

        except Exception as e:
            print(f"❌ Translation failed: {e}")
            return text

    def clean_text_for_translation(self, text: str) -> str:
        """Clean and prepare text for better translation results"""
        try:
            # Remove markdown formatting that might confuse translation APIs
            clean_text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Remove bold
            clean_text = re.sub(r"\*(.*?)\*", r"\1", clean_text)  # Remove italic
            clean_text = re.sub(r"`(.*?)`", r"\1", clean_text)  # Remove code
            clean_text = re.sub(r"#{1,6}\s*", "", clean_text)  # Remove headers

            # Clean up special characters and formatting
            clean_text = re.sub(
                r"[\r\n\t]+", " ", clean_text
            )  # Replace line breaks with space
            clean_text = re.sub(r"\s+", " ", clean_text)  # Multiple spaces to single
            clean_text = clean_text.strip()

            # Ensure sentences are properly ended
            if clean_text and not clean_text.endswith((".", "!", "?", "।")):
                clean_text += "."

            return clean_text

        except Exception as e:
            print(f"❌ Error cleaning text for translation: {e}")
            return text

    def post_process_translation(
        self, translated_text: str, target_lang: str, source_lang: str = "en"
    ) -> str:
        """Post-process translation for better readability and natural flow"""
        try:
            if not translated_text:
                return translated_text

            result = translated_text.strip()

            # Language-specific post-processing
            if target_lang == "hi":
                # Fix common Hindi translation issues
                result = result.replace("।।", "।")  # Fix double periods
                result = result.replace("..", ".")  # Fix double dots
                result = result.replace(" ।", "।")  # Remove space before period

                # Ensure proper sentence endings
                if not result.endswith(("।", "?", "!")):
                    result += "।"

                # Fix common spacing issues
                result = re.sub(
                    r"\s+([।?!])", r"\1", result
                )  # Remove space before punctuation
                result = re.sub(
                    r"([।?!])([^\s])", r"\1 \2", result
                )  # Add space after punctuation

            elif target_lang in ["bn", "te", "ta", "gu", "kn"]:
                # For other Indian languages
                result = re.sub(
                    r"\s+([।?!.])", r"\1", result
                )  # Remove space before punctuation
                result = re.sub(
                    r"([।?!.])([^\s])", r"\1 \2", result
                )  # Add space after punctuation

            else:
                # For English and other languages
                if not result.endswith((".", "?", "!")):
                    result += "."

                # Fix spacing around punctuation
                result = re.sub(r"\s+([.?!,;:])", r"\1", result)
                result = re.sub(r"([.?!:])([^\s])", r"\1 \2", result)

            # Apply pronunciation fixes if available
            if target_lang in self.pronunciation_fixes:
                fixes = self.pronunciation_fixes[target_lang]
                for original, fixed in fixes.items():
                    result = result.replace(original, fixed)

            return result.strip()

        except Exception as e:
            print(f"❌ Error post-processing translation: {e}")
            return translated_text

    def prepare_text_for_tts(self, text: str, language: str) -> str:
        """ENHANCED: Prepare text for natural TTS pronunciation"""
        try:
            if not text or not text.strip():
                return ""

            print(f"🎙️ Preparing TTS for {language}: {text[:50]}...")

            # Step 1: Clean markdown and HTML thoroughly
            clean_text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Remove bold
            clean_text = re.sub(r"\*(.*?)\*", r"\1", clean_text)  # Remove italic
            clean_text = re.sub(r"`(.*?)`", r"\1", clean_text)  # Remove code
            clean_text = re.sub(r"<[^>]+>", "", clean_text)  # Remove HTML tags
            clean_text = re.sub(r"#{1,6}\s*", "", clean_text)  # Remove headers
            clean_text = re.sub(
                r"^[\-\*\+]\s*", "", clean_text, flags=re.MULTILINE
            )  # Remove bullets
            clean_text = re.sub(
                r"^\d+\.\s*", "", clean_text, flags=re.MULTILINE
            )  # Remove numbered lists

            # Step 2: Language-specific text preparation
            if language == "hi":
                # Hindi-specific improvements
                clean_text = clean_text.replace(
                    ".", "।"
                )  # Use proper Hindi sentence ending
                clean_text = re.sub(
                    r"([।!?])\s*", r"\1 ", clean_text
                )  # Add proper pauses

                # Fix common Hindi TTS issues
                clean_text = clean_text.replace("है।", "है।")
                clean_text = clean_text.replace("हैं।", "हैं।")
                clean_text = clean_text.replace("था।", "था।")
                clean_text = clean_text.replace("थे।", "थे।")
                clean_text = clean_text.replace("करना", "करना")
                clean_text = clean_text.replace("होना", "होना")

                # Add natural breathing pauses
                clean_text = re.sub(r"(और|तथा|एवं)", r"\1, ", clean_text)
                clean_text = re.sub(r"(लेकिन|परंतु|किंतु)", r"\1, ", clean_text)

                # Fix word combinations for natural flow
                clean_text = clean_text.replace("के लिए", "के लिए")
                clean_text = clean_text.replace("की तरह", "की तरह")
                clean_text = clean_text.replace("के साथ", "के साथ")

            elif language in ["bn", "ta", "te", "gu", "kn"]:
                # For other Indian languages - add natural pauses
                clean_text = re.sub(r"([।!?.])", r"\1 ", clean_text)
                clean_text = re.sub(r"(और|তবে|மற்றும்|మరియు|અને|ಮತ್ತು)", r"\1, ", clean_text)

            elif language == "en":
                # English-specific improvements
                clean_text = re.sub(
                    r"([.!?])", r"\1 ", clean_text
                )  # Add pauses after sentences
                clean_text = re.sub(
                    r"(and|but|or|however|therefore)", r", \1", clean_text
                )  # Natural pauses

            # Step 3: Remove special characters that affect pronunciation
            clean_text = re.sub(r"[^\w\s.,!?;:\-()।]", " ", clean_text)

            # Step 4: Fix spacing and sentence structure
            clean_text = re.sub(r"\s+", " ", clean_text)  # Multiple spaces to single
            clean_text = clean_text.strip()

            # Step 5: Break long sentences for better TTS processing
            if len(clean_text) > 200:
                # Split on major punctuation
                sentences = re.split(r"[.।!?]", clean_text)
                if len(sentences) > 1:
                    # Take first few sentences that fit within reasonable TTS limit
                    result_sentences = []
                    total_length = 0

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if (
                            sentence and total_length + len(sentence) < 300
                        ):  # 300 char limit for TTS
                            result_sentences.append(sentence)
                            total_length += len(sentence)
                        else:
                            break

                    if result_sentences:
                        if language == "hi":
                            clean_text = "। ".join(result_sentences) + "।"
                        else:
                            clean_text = ". ".join(result_sentences) + "."
                    else:
                        clean_text = clean_text[:250]  # Fallback truncation
                else:
                    clean_text = clean_text[:250]

            # Step 6: Final validation and cleanup
            clean_text = clean_text.strip()

            # Ensure proper sentence ending
            if clean_text and not clean_text.endswith(("।", ".", "!", "?")):
                if language == "hi":
                    clean_text += "।"
                else:
                    clean_text += "."

            # Remove any remaining double punctuation
            clean_text = re.sub(r"([।.!?])\1+", r"\1", clean_text)

            print(f"✅ TTS text prepared: {len(clean_text)} chars")
            return clean_text

        except Exception as e:
            print(f"❌ Error preparing text for TTS: {e}")
            # Return truncated original as fallback
            return text[:200] if text else ""

    def _translate_google_free(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Enhanced Google Free Translation with better error handling"""
        try:
            url = self.apis["google_free"]["url"]
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": text,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()

            if result and isinstance(result, list) and len(result) > 0:
                translations = result[0]
                if translations and isinstance(translations, list):
                    translated_text = "".join(
                        [t[0] for t in translations if t and len(t) > 0 and t[0]]
                    )
                    return translated_text if translated_text else None

            return None

        except requests.exceptions.RequestException as e:
            print(f"Google Free API network error: {e}")
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Google Free API response parsing error: {e}")
            return None
        except Exception as e:
            print(f"Google Free API unexpected error: {e}")
            return None

    def _translate_mymemory(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """MyMemory API translation with enhanced error handling"""
        try:
            url = self.apis["mymemory"]["url"]
            params = {
                "q": text,
                "langpair": f"{source_lang}|{target_lang}",
                "de": "tatvax@education.com",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()

            if (
                result
                and "responseData" in result
                and "translatedText" in result["responseData"]
            ):
                translation = result["responseData"]["translatedText"]
                if translation and translation.strip() and translation != text:
                    return translation

            return None

        except Exception as e:
            print(f"MyMemory API error: {e}")
            return None

    def _translate_libretranslate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """LibreTranslate API translation with enhanced error handling"""
        try:
            url = self.apis["libretranslate"]["url"]
            data = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            }

            response = requests.post(url, json=data, timeout=15)
            response.raise_for_status()

            result = response.json()

            if result and "translatedText" in result:
                translation = result["translatedText"]
                if translation and translation.strip() and translation != text:
                    return translation

            return None

        except Exception as e:
            print(f"LibreTranslate API error: {e}")
            return None

    def _translate_fallback(self, text: str, source_lang: str, target_lang: str) -> str:
        """Enhanced fallback translation using comprehensive dictionary"""
        try:
            fallback_key = f"{source_lang}_to_{target_lang}"

            if fallback_key not in self.fallback_dict:
                return text

            dictionary = self.fallback_dict[fallback_key]
            translated_text = text

            # Sort by length (longer phrases first) for better matching
            sorted_terms = sorted(
                dictionary.items(), key=lambda x: len(x[0]), reverse=True
            )

            for original, translation in sorted_terms:
                # Use word boundaries for better matching
                pattern = r"\b" + re.escape(original) + r"\b"
                translated_text = re.sub(
                    pattern, translation, translated_text, flags=re.IGNORECASE
                )

            # If significant translation occurred, mark as successful
            if translated_text != text:
                print(
                    f"✅ Fallback translation applied: {len([k for k, v in dictionary.items() if k.lower() in text.lower()])} terms matched"
                )

            return translated_text

        except Exception as e:
            print(f"❌ Fallback translation error: {e}")
            return text

    def validate_translation_quality(
        self, original: str, translated: str, source_lang: str, target_lang: str
    ) -> bool:
        """Enhanced validation of translation quality"""
        try:
            # Basic checks
            if not translated or not translated.strip():
                return False

            # Check if translation is identical to original (might indicate failure)
            if original.strip().lower() == translated.strip().lower():
                return False

            # Check if translation is too short compared to original (might be truncated)
            if len(translated) < len(original) * 0.3 and len(original) > 50:
                return False

            # Check if translation contains error indicators
            error_indicators = [
                "error",
                "failed",
                "timeout",
                "invalid",
                "could not",
                "unable to",
            ]
            if any(indicator in translated.lower() for indicator in error_indicators):
                return False

            # Check for API error messages
            api_errors = [
                "api key",
                "rate limit",
                "quota exceeded",
                "service unavailable",
            ]
            if any(error in translated.lower() for error in api_errors):
                return False

            # Language-specific validations
            if target_lang == "hi":
                # Hindi should contain Devanagari characters
                devanagari_chars = sum(
                    1 for char in translated if "\u0900" <= char <= "\u097f"
                )
                if len(translated) > 10 and devanagari_chars == 0:
                    return False

            return True

        except Exception as e:
            print(f"❌ Error validating translation: {e}")
            return True  # Default to accepting translation

    def get_tts_language_code(self, lang_code: str, text: str = "") -> str:
        """Get proper TTS language code with text analysis for better pronunciation"""
        try:
            # Basic mapping with fallbacks
            tts_mapping = {
                "en": "en",
                "hi": "hi",
                "bn": "bn",
                "mr": "hi",  # Use Hindi TTS for Marathi (similar script)
                "te": "te",
                "ta": "ta",
                "gu": "gu",
                "kn": "kn",
            }

            base_lang = tts_mapping.get(lang_code, "en")

            # If we have text, we can potentially improve the language selection
            if text and lang_code in ["hi", "mr"]:
                # For Devanagari script languages, check for language-specific indicators
                marathi_indicators = ["आहे", "माझे", "तुझे", "काय", "कसे", "कुठे", "केव्हा"]
                if any(word in text for word in marathi_indicators):
                    return "hi"  # Use Hindi TTS even for Marathi
                return "hi"

            return base_lang

        except Exception as e:
            print(f"❌ Error getting TTS language code: {e}")
            return "en"

    def batch_translate(
        self, texts: List[str], target_lang: str = "en", source_lang: str = "auto"
    ) -> List[str]:
        """Translate multiple texts efficiently with rate limiting"""
        try:
            results = []
            for i, text in enumerate(texts):
                if i > 0:  # Add delay between requests to avoid rate limiting
                    time.sleep(0.5)
                translated = self.translate_text(text, target_lang, source_lang)
                results.append(translated)
            return results
        except Exception as e:
            print(f"❌ Batch translation error: {e}")
            return texts

    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages"""
        return self.language_codes

    def is_language_supported(self, lang_code: str) -> bool:
        """Check if language is supported"""
        return lang_code in self.language_codes

    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name"""
        return self.language_codes.get(lang_code, lang_code)

    def get_translation_stats(self) -> Dict:
        """Get translation service statistics"""
        try:
            active_apis = [
                name for name, config in self.apis.items() if config["active"]
            ]
            return {
                "supported_languages": len(self.language_codes),
                "fallback_terms": sum(
                    len(terms) for terms in self.fallback_dict.values()
                ),
                "active_apis": len(active_apis),
                "api_list": active_apis,
                "tts_languages": len(self.tts_language_mapping),
            }
        except Exception as e:
            print(f"❌ Error getting translation stats: {e}")
            return {}
