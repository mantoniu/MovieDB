const form = document.getElementById("name-form");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const username = String(data.get("username") || "").trim();
  if (!username) {
    return;
  }
  localStorage.setItem("moviedb_username", username);
  window.location.href = `/app?user=${encodeURIComponent(username)}`;
});
