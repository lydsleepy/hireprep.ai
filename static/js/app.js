/**
 * app.js — hireprep.ai frontend
 *
 * All UI state lives in `appState`. No localStorage, no sessionStorage.
 * Page refresh = clean slate.
 */

// ============================================================
// State
// ============================================================

const appState = {
  resumeFile: null,         // File object | null
  jdText: "",
  currentFeature: null,     // last triggered feature key
  currentOutput: null,      // last generated text
  isLoading: false,
};

// Feature metadata
const FEATURES = {
  cover_letter:        { title: "Your cover letter",          filename: "cover_letter" },
  practice_questions:  { title: "Practice questions",         filename: "practice_questions" },
  resume_questions:    { title: "Resume-specific questions",  filename: "resume_questions" },
  tailored_resume:     { title: "Your tailored resume",       filename: "tailored_resume" },
};

// ============================================================
// DOM refs
// ============================================================

const dropZone        = document.getElementById("drop-zone");
const fileInput       = document.getElementById("resume-file-input");
const filePreview     = document.getElementById("file-preview");
const fileName        = document.getElementById("file-name");
const fileSize        = document.getElementById("file-size");
const fileRemove      = document.getElementById("file-remove");
const jdTextarea      = document.getElementById("jd-textarea");
const charCount       = document.getElementById("char-count");
const actionCards     = document.querySelectorAll(".action-card");
const outputSection   = document.getElementById("output-section");
const outputTitle     = document.getElementById("output-title");
const outputText      = document.getElementById("output-text");
const outputSkeleton  = document.getElementById("output-skeleton");
const btnCopy         = document.getElementById("btn-copy");
const copyLabel       = document.getElementById("copy-label");
const btnDownloadPdf  = document.getElementById("btn-download-pdf");
const btnDownloadDocx = document.getElementById("btn-download-docx");
const btnRegenerate   = document.getElementById("btn-regenerate");
const btnCloseOutput  = document.getElementById("btn-close-output");
const modalBackdrop   = document.getElementById("modal-backdrop");
const modalTitle      = document.getElementById("modal-title");
const modalMessage    = document.getElementById("modal-message");
const modalClose      = document.getElementById("modal-close");
const footerYear      = document.getElementById("footer-year");

// ============================================================
// Init
// ============================================================

footerYear.textContent = new Date().getFullYear();

// ============================================================
// Drop zone — file upload
// ============================================================

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTS   = new Set([".pdf", ".docx", ".doc"]);

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFileSelected(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) handleFileSelected(file);
  // Reset input so the same file can be re-selected after removal
  fileInput.value = "";
});

fileRemove.addEventListener("click", clearResume);

function handleFileSelected(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();

  if (!ALLOWED_EXTS.has(ext)) {
    showModal("Invalid file type", "That file format isn't supported. Please upload a .pdf or .docx file.");
    return;
  }

  if (file.size > MAX_FILE_BYTES) {
    showModal("File too large", "Files must be 5 MB or smaller.");
    return;
  }

  appState.resumeFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  dropZone.classList.add("hidden");
  filePreview.classList.remove("hidden");
}

function clearResume() {
  appState.resumeFile = null;
  filePreview.classList.add("hidden");
  dropZone.classList.remove("hidden");
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ============================================================
// JD textarea — live character count + auto-resize
// ============================================================

jdTextarea.addEventListener("input", () => {
  appState.jdText = jdTextarea.value;
  const n = jdTextarea.value.length;
  charCount.textContent = n === 1 ? "1 character" : `${n.toLocaleString()} characters`;

  // Auto-resize (capped by CSS max-height)
  jdTextarea.style.height = "auto";
  jdTextarea.style.height = jdTextarea.scrollHeight + "px";
});

// ============================================================
// Action cards
// ============================================================

actionCards.forEach((card) => {
  card.addEventListener("click", () => {
    const feature = card.dataset.feature;
    triggerFeature(feature, card);
  });
});

async function triggerFeature(feature, triggerCard) {
  if (appState.isLoading) return;

  const jd = jdTextarea.value.trim();
  const hasResume = Boolean(appState.resumeFile);
  const needsResume = feature !== "practice_questions";

  // Client-side validation
  if (!hasResume && !jd) {
    if (needsResume) {
      showModal("Missing inputs", "This feature needs both a resume and a job description. Please upload your resume and paste the job description.");
    } else {
      // practice_questions only needs a JD
      showModal("Missing job description", "Please paste a job description to use this feature.");
    }
    return;
  }
  if (needsResume && !hasResume) {
    showModal("Missing resume", "Please upload your resume to use this feature.");
    return;
  }
  if (!jd) {
    showModal("Missing job description", "Please paste a job description to use this feature.");
    return;
  }

  appState.currentFeature = feature;
  setLoading(true, triggerCard);
  showOutputSkeleton(feature);

  try {
    const formData = new FormData();
    formData.append("jd_text", jd);
    if (appState.resumeFile) formData.append("resume_file", appState.resumeFile);

    const res = await fetch(`/api/generate/${feature}`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "An unexpected error occurred." }));
      throw new Error(body.detail || "An unexpected error occurred.");
    }

    const data = await res.json();
    appState.currentOutput = data.output;
    renderOutput(feature, data.output);
  } catch (err) {
    hideOutputSkeleton();
    showModal("Error", err.message);
  } finally {
    setLoading(false, triggerCard);
  }
}

// ============================================================
// Loading state
// ============================================================

function setLoading(loading, activeCard) {
  appState.isLoading = loading;
  actionCards.forEach((card) => {
    const spinner = card.querySelector(".spinner");
    const iconWrap = card.querySelector(".action-icon-wrap");
    if (card === activeCard) {
      if (loading) {
        card.classList.add("loading");
        spinner?.classList.remove("hidden");
        iconWrap?.classList.add("hidden");
      } else {
        card.classList.remove("loading");
        spinner?.classList.add("hidden");
        iconWrap?.classList.remove("hidden");
      }
    } else {
      card.classList.toggle("dimmed", loading);
    }
  });
}

// ============================================================
// Output rendering
// ============================================================

function showOutputSkeleton(feature) {
  outputSection.classList.remove("hidden");
  outputTitle.textContent = FEATURES[feature]?.title ?? "Output";
  outputText.classList.add("hidden");
  outputSkeleton.classList.remove("hidden");
  outputSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function hideOutputSkeleton() {
  // Called on error — hide skeleton but don't reveal empty output-text
  outputSkeleton.classList.add("hidden");
  outputSection.classList.add("hidden");
}

function renderOutput(feature, text) {
  outputTitle.textContent = FEATURES[feature]?.title ?? "Output";
  outputText.textContent = text;
  outputSkeleton.classList.add("hidden");
  outputText.classList.remove("hidden");
  outputSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

btnCloseOutput.addEventListener("click", () => {
  outputSection.classList.add("hidden");
  appState.currentOutput = null;
  appState.currentFeature = null;
});

btnRegenerate.addEventListener("click", () => {
  if (!appState.currentFeature || appState.isLoading) return;
  const card = document.querySelector(`[data-feature="${appState.currentFeature}"]`);
  triggerFeature(appState.currentFeature, card);
});

// ============================================================
// Copy
// ============================================================

btnCopy.addEventListener("click", async () => {
  if (!appState.currentOutput) return;
  try {
    await navigator.clipboard.writeText(appState.currentOutput);
    copyLabel.textContent = "Copied";
    btnCopy.querySelector("svg").style.stroke = "var(--success)";
    setTimeout(() => {
      copyLabel.textContent = "Copy";
      btnCopy.querySelector("svg").style.stroke = "";
    }, 1500);
  } catch {
    showModal("Copy failed", "Your browser blocked clipboard access. Please select the text and copy manually.");
  }
});

// ============================================================
// Download
// ============================================================

async function downloadOutput(format) {
  if (!appState.currentOutput || !appState.currentFeature) return;
  const filename = FEATURES[appState.currentFeature]?.filename ?? "hireprep_output";

  try {
    const res = await fetch(`/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: appState.currentOutput, filename }),
    });

    if (!res.ok) throw new Error("Export failed. Please try again.");

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${filename}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    showModal("Download failed", err.message);
  }
}

btnDownloadPdf.addEventListener("click",  () => downloadOutput("pdf"));
btnDownloadDocx.addEventListener("click", () => downloadOutput("docx"));

// ============================================================
// Modal
// ============================================================

function showModal(title, message) {
  modalTitle.textContent   = title;
  modalMessage.textContent = message;
  modalBackdrop.classList.remove("hidden");
  modalClose.focus();
}

function closeModal() {
  modalBackdrop.classList.add("hidden");
}

modalClose.addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalBackdrop.classList.contains("hidden")) {
    closeModal();
  }
});
