const userNameEl = document.getElementById("user-name");
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const recText = document.getElementById("rec-text");
const recList = document.getElementById("rec-list");
const refList = document.getElementById("ref-list");
const refTitle = document.getElementById("ref-title");
const refToggle = document.getElementById("ref-toggle");
const refBlock = document.getElementById("ref-block");
const panelSelect = document.getElementById("panel-select");
const layout = document.querySelector(".layout");
const recPanel = document.querySelector(".rec-panel");
const reviewPanel = document.getElementById("review-panel");
const reviewForm = document.getElementById("review-form");
const reviewScore = document.getElementById("review-score");
const reviewScoreValue = document.getElementById("review-score-value");
const reviewTitle = document.getElementById("review-title");
const movieSuggestions = document.getElementById("movie-suggestions");
const reviewText = document.getElementById("review-text");
const reviewSpoiler = document.getElementById("review-spoiler");
const reviewError = document.getElementById("review-error");

const MAX_REF_VISIBLE = 6;
let refCollapsed = true;
let recLoaded = false;
let movieTitles = [];
let movieTitleToId = new Map();
const refreshBtn = document.getElementById("refresh-rec");
const modal = document.getElementById("synopsis-modal");
const modalTitle = document.getElementById("modal-title");
const modalMeta = document.getElementById("modal-meta");
const modalBody = document.getElementById("modal-body");
const modalClose = document.getElementById("modal-close");

function getUserName() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("user");
  const fromStorage = localStorage.getItem("moviedb_username");
  return (fromQuery || fromStorage || "").trim();
}

const username = getUserName();
if (!username) {
  window.location.href = "/";
}

userNameEl.textContent = username || "-";

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = role === "user" ? "Toi" : "Agent";

  const body = document.createElement("div");
  body.className = "content";
  if (role === "agent" && window.marked) {
    body.innerHTML = window.marked.parse(text, { breaks: true });
  } else {
    body.textContent = text;
  }

  wrapper.appendChild(meta);
  wrapper.appendChild(body);
  const emptyState = chatLog.querySelector(".empty-chat");
  if (emptyState) {
    emptyState.remove();
  }
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function openModal(rec) {
  modalTitle.textContent = rec.title || "Synopsis";
  const parts = [];
  if (rec.year && rec.year !== "N/A") {
    parts.push(rec.year);
  }
  if (rec.genres && rec.genres !== "N/A") {
    parts.push(rec.genres);
  }
  if (rec.tconst && rec.tconst !== "N/A") {
    parts.push(rec.tconst);
  }
  if (typeof rec.score === "number") {
    parts.push(`Score ${rec.score.toFixed(3)}`);
  }
  modalMeta.textContent = parts.join(" · ");
  modalBody.textContent = rec.synopsis || "";
  modal.classList.remove("hidden");
}

function closeModal() {
  modal.classList.add("hidden");
}

modalClose.addEventListener("click", closeModal);
modal.addEventListener("click", (event) => {
  if (event.target.classList.contains("modal-backdrop")) {
    closeModal();
  }
});

async function sendChat(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Chat error");
  }
  return data.response || "";
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }

  appendMessage("user", message);
  chatInput.value = "";
  chatInput.focus();

  try {
    const reply = await sendChat(message);
    appendMessage("agent", reply);
  } catch (error) {
    appendMessage("agent", `Erreur: ${error.message}`);
  }
});

function renderRecommendations(list) {
  recList.innerHTML = "";
  if (!list.length) {
    recText.style.display = "none";
    return;
  }
  recText.textContent = "";
  recText.style.display = "none";

  list.forEach((rec) => {
    const card = document.createElement("div");
    card.className = "rec-card";

    const title = document.createElement("div");
    title.className = "rec-title";
    title.textContent = `${rec.title} (${rec.year})`;

    const meta = document.createElement("div");
    meta.className = "rec-meta";
    const score = Number(rec.score || 0).toFixed(3);
    meta.textContent = `Score ${score} · ${rec.genres || "Genres N/A"} · ${rec.tconst}`;

    card.appendChild(title);
    card.appendChild(meta);

    if (rec.synopsis) {
      const synopsis = document.createElement("div");
      synopsis.className = "rec-synopsis";
      const trimmed = rec.synopsis.length > 220
        ? `${rec.synopsis.slice(0, 220).trim()}...`
        : rec.synopsis;
      synopsis.textContent = trimmed;
      card.appendChild(synopsis);

      if (rec.synopsis.length > 220) {
        const moreBtn = document.createElement("button");
        moreBtn.type = "button";
        moreBtn.className = "rec-more";
        moreBtn.textContent = "Voir plus";
        moreBtn.addEventListener("click", () => {
          openModal(rec);
        });
        card.appendChild(moreBtn);
      }
    }

    recList.appendChild(card);
  });
}

function renderReferenceMovies(list) {
  refList.innerHTML = "";
  refTitle.style.display = "none";
  refToggle.style.display = "none";
  refBlock.classList.remove("expanded");
  if (!list.length) {
    const empty = document.createElement("div");
    empty.className = "rec-meta";
    empty.textContent = "Aucun film de reference disponible.";
    refList.appendChild(empty);
    refTitle.style.display = "block";
    return;
  }

  refTitle.style.display = "block";
  list.forEach(([title, rating], index) => {
    const pill = document.createElement("div");
    pill.className = "ref-pill";
    const titleSpan = document.createElement("span");
    titleSpan.className = "ref-title";
    titleSpan.textContent = title;

    const ratingSpan = document.createElement("span");
    ratingSpan.className = "ref-rating";
    ratingSpan.textContent = `${rating}/10`;

    pill.appendChild(titleSpan);
    pill.appendChild(ratingSpan);
    if (refCollapsed && index >= MAX_REF_VISIBLE) {
      pill.style.display = "none";
    }
    refList.appendChild(pill);
  });

  if (list.length > MAX_REF_VISIBLE) {
    refToggle.style.display = "inline-flex";
    const remaining = list.length - MAX_REF_VISIBLE;
    refToggle.textContent = refCollapsed
      ? `▼ ${remaining} autres films`
      : "▲ Masquer";
  }
}

refToggle.addEventListener("click", () => {
  refCollapsed = !refCollapsed;
  const pills = Array.from(refList.children);
  pills.forEach((pill, index) => {
    if (pill.classList.contains("rec-meta")) {
      return;
    }
    if (index >= MAX_REF_VISIBLE) {
      pill.style.display = refCollapsed ? "none" : "flex";
    }
  });
  refBlock.classList.toggle("expanded", !refCollapsed);
  const total = pills.filter((pill) => pill.classList.contains("ref-pill"))
    .length;
  const remaining = Math.max(total - MAX_REF_VISIBLE, 0);
  refToggle.textContent = refCollapsed
    ? `▼ ${remaining} autres films`
    : "▲ Masquer";
});

async function loadRecommendations() {
  recText.textContent = "Chargement des recommandations...";
  recText.style.display = "block";
  recList.innerHTML = "";
  refList.innerHTML = "";
  refTitle.style.display = "none";
  refToggle.style.display = "none";
  try {
    const response = await fetch(
      `/api/recommendations?username=${encodeURIComponent(username)}`
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Recommendation error");
    }
    refCollapsed = true;
    renderReferenceMovies(data.reference_movies || []);
    renderRecommendations(data.recommendations || []);
  } catch (error) {
    recList.innerHTML = "";
    refList.innerHTML = "";
    refTitle.style.display = "none";
    refToggle.style.display = "none";
    recText.textContent = `Erreur: ${error.message}`;
    recText.style.display = "block";
  }
}

refreshBtn.addEventListener("click", loadRecommendations);

function setRightPanel(value) {
  const selected = value || "recommendations";
  const showRec = selected === "recommendations";
  const showReview = selected === "review";
  recPanel.classList.toggle("is-hidden", !showRec);
  reviewPanel.classList.toggle("is-hidden", !showReview);
  layout.classList.toggle("single", false);
  clearReviewForm();
  if (showRec) {
    recLoaded = true;
    loadRecommendations();
  }
}

panelSelect.addEventListener("change", (event) => {
  setRightPanel(event.target.value);
});

function updateMovieSuggestions(query) {
  if (!movieSuggestions) {
    return;
  }
  movieSuggestions.innerHTML = "";
  const value = query.trim().toLowerCase();
  if (!value) {
    return;
  }
  const matches = movieTitles
    .filter((title) => title.toLowerCase().includes(value))
    .slice(0, 12);
  matches.forEach((title) => {
    const option = document.createElement("option");
    option.value = title;
    movieSuggestions.appendChild(option);
  });
}

async function loadMovieTitles() {
  if (!reviewTitle) {
    return;
  }
  try {
    const response = await fetch("/api/movies");
    const data = await response.json();
    if (!response.ok) {
      return;
    }
    if (data && typeof data.movies === "object" && data.movies !== null) {
      movieTitles = Object.values(data.movies);
      movieTitleToId = new Map(
        Object.entries(data.movies).map(([id, title]) => [String(title).toLowerCase(), id])
      );
    } else if (Array.isArray(data.titles)) {
      movieTitles = data.titles;
      movieTitleToId = new Map(
        movieTitles.map((title) => [String(title).toLowerCase(), title])
      );
    } else {
      movieTitles = [];
      movieTitleToId = new Map();
    }
  } catch (error) {
    movieTitles = [];
    movieTitleToId = new Map();
  }
}

if (reviewTitle) {
  reviewTitle.addEventListener("input", (event) => {
    updateMovieSuggestions(event.target.value);
  });
}

function setReviewError(message) {
  if (!reviewError) {
    return;
  }
  reviewError.textContent = message || "";
  reviewError.style.display = message ? "block" : "none";
  reviewError.classList.remove("success");
}

function setReviewSuccess(message) {
  if (!reviewError) {
    return;
  }
  reviewError.textContent = message || "";
  reviewError.style.display = message ? "block" : "none";
  if (message) {
    reviewError.classList.add("success");
  } else {
    reviewError.classList.remove("success");
  }
}

function clearReviewInputs() {
  if (reviewTitle) {
    reviewTitle.value = "";
  }
  if (reviewText) {
    reviewText.value = "";
  }
  if (reviewSpoiler) {
    reviewSpoiler.checked = false;
  }
  if (reviewScore) {
    reviewScore.value = "5";
  }
  if (reviewScoreValue) {
    reviewScoreValue.textContent = Number(reviewScore.value).toFixed(1);
  }
  if (movieSuggestions) {
    movieSuggestions.innerHTML = "";
  }
}

function clearReviewForm() {
  clearReviewInputs();
  setReviewError("");
  setReviewSuccess("");
}

async function submitReview() {
  if (!reviewTitle || !reviewScore) {
    return;
  }
  const title = reviewTitle.value.trim();
  const rating = reviewScore.value;
  const spoiler = reviewSpoiler ? reviewSpoiler.checked : false;
  const text = reviewText ? reviewText.value.trim() : "";

  if (!title) {
    setReviewError("Le titre du film est obligatoire.");
    return;
  }
  if (!rating) {
    setReviewError("La note est obligatoire.");
    return;
  }
  const movieId = movieTitleToId.get(title.toLowerCase());
  if (!movieId) {
    setReviewError(`Le film ${title} n'existe pas dans la base de donnees.`);
    return;
  }

  setReviewError("");
  try {
    const response = await fetch("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        movie_id: movieId,
        title,
        rating: Number(rating),
        spoiler,
        text,
        username,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setReviewError(data.error || "Erreur lors de l'envoi.");
      return;
    }
    setReviewSuccess("Avis envoye avec succes.");
    clearReviewInputs();
  } catch (error) {
    setReviewError("Erreur lors de l'envoi.");
  }
}

if (reviewForm) {
  reviewForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitReview();
  });
}

if (reviewScore && reviewScoreValue) {
  const updateScore = () => {
    reviewScoreValue.textContent = Number(reviewScore.value).toFixed(1);
  };
  reviewScore.addEventListener("input", updateScore);
  updateScore();
}

loadMovieTitles();
setRightPanel(panelSelect.value);
