// Module 2, steps 1–2 (report section 4.3.2): detect the face and check image quality.
// Runs entirely in the browser. The photo is never uploaded or stored.
//
// Skin-characteristic estimates (the transfer-learning CNN, steps 3–7) are not shipped yet;
// until that model is trained and evaluated, the profile comes from the questionnaire only.

export const THRESHOLDS = {
  minSide: 300,        // pixels on the shorter side of the original image
  minBrightness: 60,   // mean luma, 0–255
  maxBrightness: 200,
  minSharpness: 40,    // variance of the Laplacian on the 512-px working copy
};

const MP_VERSION = "0.10.14";
const MP_BASE = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite";

let detectorPromise;
function getDetector() {
  if (!detectorPromise) {
    detectorPromise = (async () => {
      const vision = await import(`${MP_BASE}/vision_bundle.mjs`);
      const fileset = await vision.FilesetResolver.forVisionTasks(`${MP_BASE}/wasm`);
      return vision.FaceDetector.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL },
        runningMode: "IMAGE",
        minDetectionConfidence: 0.5,
      });
    })().catch((err) => {
      detectorPromise = undefined;
      throw err;
    });
  }
  return detectorPromise;
}

export async function loadImage(file) {
  const url = URL.createObjectURL(file);
  try {
    return await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Not a readable image"));
      img.src = url;
    });
  } finally {
    // The pixels stay in the Image element in memory only.
    URL.revokeObjectURL(url);
  }
}

function toWorkingCanvas(img, maxSide = 512) {
  const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const w = Math.round(img.naturalWidth * scale);
  const h = Math.round(img.naturalHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, w, h);
  return { canvas, ctx, w, h };
}

function grayscale(data, w, h) {
  const g = new Float32Array(w * h);
  for (let i = 0, j = 0; j < g.length; i += 4, j++) {
    g[j] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }
  return g;
}

// Variance of the 4-neighbour Laplacian over a region (same measure as OpenCV's
// cv2.Laplacian(gray, CV_64F).var() with the default 3×3 kernel).
function laplacianVariance(g, w, region) {
  const { x0, y0, x1, y1 } = region;
  let sum = 0;
  let sumSq = 0;
  let n = 0;
  for (let y = Math.max(1, y0); y < Math.min(y1, g.length / w - 1); y++) {
    for (let x = Math.max(1, x0); x < Math.min(x1, w - 1); x++) {
      const i = y * w + x;
      const v = g[i - w] + g[i + w] + g[i - 1] + g[i + 1] - 4 * g[i];
      sum += v;
      sumSq += v * v;
      n++;
    }
  }
  if (!n) return 0;
  const mean = sum / n;
  return sumSq / n - mean * mean;
}

function meanOver(g, w, region) {
  let s = 0;
  let n = 0;
  for (let y = region.y0; y < region.y1; y++) {
    for (let x = region.x0; x < region.x1; x++) {
      s += g[y * w + x];
      n++;
    }
  }
  return n ? s / n : 0;
}

export async function checkPhoto(img) {
  const { canvas, ctx, w, h } = toWorkingCanvas(img);
  const g = grayscale(ctx.getImageData(0, 0, w, h).data, w, h);
  const checks = [];

  const shortSide = Math.min(img.naturalWidth, img.naturalHeight);
  checks.push({
    id: "size", ok: shortSide >= THRESHOLDS.minSide,
    label: shortSide >= THRESHOLDS.minSide ? `Resolution is fine (${img.naturalWidth}×${img.naturalHeight})` : `Too small (${img.naturalWidth}×${img.naturalHeight}). Use at least ${THRESHOLDS.minSide} px on the short side.`,
  });

  let faces = null;
  let faceError = null;
  try {
    const detector = await getDetector();
    faces = detector.detect(canvas).detections;
  } catch (err) {
    faceError = err;
  }

  let region = { x0: 0, y0: 0, x1: w, y1: h };
  if (faces) {
    if (faces.length === 1) {
      const b = faces[0].boundingBox;
      region = {
        x0: Math.max(0, Math.floor(b.originX)), y0: Math.max(0, Math.floor(b.originY)),
        x1: Math.min(w, Math.ceil(b.originX + b.width)), y1: Math.min(h, Math.ceil(b.originY + b.height)),
      };
      const score = faces[0].categories?.[0]?.score;
      checks.push({ id: "face", ok: true, label: `One face found${score ? ` (confidence ${(score * 100).toFixed(0)}%)` : ""}` });
    } else {
      checks.push({ id: "face", ok: false, label: faces.length ? `${faces.length} faces found. Use a photo with only you in it.` : "No face found. Face the camera in good light." });
    }
  } else {
    checks.push({ id: "face", ok: null, label: "The face detector could not load (offline?), so this check was skipped." });
  }

  const brightness = meanOver(g, w, region);
  const bOk = brightness >= THRESHOLDS.minBrightness && brightness <= THRESHOLDS.maxBrightness;
  checks.push({
    id: "light", ok: bOk,
    label: bOk ? `Lighting looks even (brightness ${brightness.toFixed(0)}/255)`
      : brightness < THRESHOLDS.minBrightness ? `Too dark (brightness ${brightness.toFixed(0)}/255). Face a window or a lamp.`
        : `Too bright (brightness ${brightness.toFixed(0)}/255). Move out of direct light.`,
  });

  const sharp = laplacianVariance(g, w, region);
  const sOk = sharp >= THRESHOLDS.minSharpness;
  checks.push({
    id: "sharp", ok: sOk,
    label: sOk ? `Sharp enough (focus score ${sharp.toFixed(0)})` : `Looks blurry (focus score ${sharp.toFixed(0)}, needs ${THRESHOLDS.minSharpness}). Hold still or tap to focus.`,
  });

  // Draw the face box on the preview.
  if (faces && faces.length) {
    ctx.strokeStyle = "#b9684a";
    ctx.lineWidth = Math.max(2, w / 160);
    for (const f of faces) {
      const b = f.boundingBox;
      ctx.strokeRect(b.originX, b.originY, b.width, b.height);
    }
  }

  const usable = checks.every((c) => c.ok !== false);
  return { canvas, checks, usable, faceError };
}
