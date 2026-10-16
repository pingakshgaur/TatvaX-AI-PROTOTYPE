// Prepare a photo for the tutor: downscale and re-encode as JPEG so it uploads quickly on
// slow connections and stays under the server's size limit (about 1.1 MB once encoded).
const LIMIT = 1_450_000; // characters of the data URL

export async function preparePhoto(file) {
  if (!file || !/^image\//.test(file.type)) throw new Error("Choose a photo or picture file.");
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error("That picture couldn't be opened."));
      el.src = url;
    });
    for (const [side, quality] of [[1600, 0.85], [1280, 0.75], [1024, 0.65], [800, 0.6]]) {
      const scale = Math.min(1, side / Math.max(img.naturalWidth, img.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#ffffff"; // transparent PNGs become white, not black
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", quality);
      if (dataUrl.length <= LIMIT) return { dataUrl, name: file.name || "photo" };
    }
    throw new Error("That picture is too large. Try a smaller one.");
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Saved questions that came with a photo start with this marker (the photo itself isn't kept).
export const PHOTO_MARK = "[Photo] ";
