// What a device keeps about the person using it. School computers are shared, so when an account
// signs out (or a different account signs in), everything personal kept in the browser goes:
// translation history, reminders, quiz drafts and the offline copies of their profile and progress.
// Device preferences (theme, sound, language) stay.

const KEEP = new Set(["tatvax.theme", "tatvax.sound", "tatvax.lang"]);
const ACCOUNT_KEY = "tatvax.account";
const SHARED_API = /^\/api\/library(\/[^/]+)?$/; // the notes themselves, not who has read them

function storage() {
  try { return window.localStorage; } catch { return null; }
}

export async function forgetUserData() {
  const store = storage();
  try {
    Object.keys(store || {}).filter((key) => key.startsWith("tatvax.") && !KEEP.has(key)).forEach((key) => store.removeItem(key));
  } catch { /* storage unavailable */ }
  try {
    if (!("caches" in window)) return; // only on https or localhost
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        const path = new URL(request.url).pathname;
        // The school's study notes are the same for everyone, so they stay for offline reading.
        if (path.startsWith("/api/") && !SHARED_API.test(path)) await cache.delete(request);
      }
    }
  } catch { /* cache unavailable */ }
}

// Called whenever the signed-in user changes. A guest becoming an account keeps their data; a
// registered account being replaced (sign-out, another sign-in, an expired session) clears it.
export function noteUser(user) {
  const store = storage();
  let previous = null;
  try { previous = store?.getItem(ACCOUNT_KEY); } catch { /* unavailable */ }
  const current = user && !user.is_guest ? String(user.id) : null;
  if (previous && previous !== current) forgetUserData();
  try {
    if (current) store?.setItem(ACCOUNT_KEY, current);
    else store?.removeItem(ACCOUNT_KEY);
  } catch { /* unavailable */ }
}
