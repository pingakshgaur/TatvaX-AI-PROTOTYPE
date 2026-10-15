// Voice input (Web Speech API in the browser) and read-aloud: a browser voice when one exists
// for the language, otherwise server-side gTTS audio.

const Recognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export const canListen = Boolean(Recognition);

export function listen(locale, { onInterim, onFinal, onEnd, onError } = {}) {
  if (!Recognition) throw new Error("unsupported");
  const recognition = new Recognition();
  recognition.lang = locale;
  recognition.interimResults = true;
  recognition.continuous = false;

  let finalText = "";
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) finalText += result[0].transcript;
      else interim += result[0].transcript;
    }
    onInterim?.(finalText + interim);
  };
  recognition.onerror = (event) => onError?.(event.error);
  recognition.onend = () => {
    if (finalText.trim()) onFinal?.(finalText.trim());
    onEnd?.();
  };
  recognition.start();
  return () => recognition.stop();
}

let audio = null;
let finish = null;

function browserVoice(langCode) {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang.toLowerCase().startsWith(`${langCode}-in`))
    || voices.find((v) => v.lang.toLowerCase().split("-")[0] === langCode)
    || null;
}

export function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  if (audio) {
    audio.pause();
    URL.revokeObjectURL(audio.src);
    audio = null;
  }
  if (finish) {
    const done = finish;
    finish = null;
    done();
  }
}

// Resolves when speech ends or is stopped; rejects when no voice is available.
export function speak(text, { langCode, serverLanguages = [] }) {
  stopSpeaking();
  return new Promise((resolve, reject) => {
    finish = resolve;
    const voice = browserVoice(langCode);
    if (voice) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.voice = voice;
      utterance.lang = voice.lang;
      utterance.rate = 0.95;
      utterance.onend = stopSpeaking;
      utterance.onerror = stopSpeaking;
      window.speechSynthesis.speak(utterance);
      return;
    }
    if (!serverLanguages.includes(langCode)) {
      finish = null;
      reject(new Error("no-voice"));
      return;
    }
    fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: langCode }),
    })
      .then((response) => {
        if (!response.ok) throw new Error("tts-failed");
        return response.blob();
      })
      .then((blob) => {
        if (finish !== resolve) return; // stopped while loading
        audio = new Audio(URL.createObjectURL(blob));
        audio.onended = stopSpeaking;
        audio.onerror = stopSpeaking;
        return audio.play();
      })
      .catch((err) => {
        finish = null;
        reject(err);
      });
  });
}

if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.addEventListener?.("voiceschanged", () => window.speechSynthesis.getVoices());
}
