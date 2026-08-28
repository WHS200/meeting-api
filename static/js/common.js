let currentUserPromise = null;
function getCurrentUser() {
  if (!currentUserPromise) {
    currentUserPromise = apiFetch("/api/users/me").catch((error) => {
      if (error.status === 401) return null;
      throw error;
    });
  }
  return currentUserPromise;
}
async function requireLogin() {
  const user = await getCurrentUser();
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    location.href = `/static/login.html?next=${next}`;
    return null;
  }
  return user;
}
async function initializeHeader() {
  try {
    const user = await getCurrentUser();
    document
      .querySelectorAll("[data-auth-guest]")
      .forEach((el) => (el.hidden = Boolean(user)));
    document
      .querySelectorAll("[data-auth-user]")
      .forEach((el) => (el.hidden = !user));
    if (user) {
      document
        .querySelectorAll("[data-user-initial]")
        .forEach((el) => (el.textContent = (user.nickname || "?").slice(0, 1)));
      document
        .querySelectorAll("[data-user-nickname]")
        .forEach((el) => (el.textContent = user.nickname || "내 프로필"));
    }
  } catch (error) {
    showToast(error.message);
  }
  document.querySelectorAll("[data-logout]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        await apiFetch("/api/auth/logout", { method: "POST" });
        location.href = "/static/login.html";
      } catch (error) {
        showToast(error.message);
      }
    }),
  );
  document.querySelectorAll("[data-global-search]").forEach((form) =>
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const keyword = form.keyword.value.trim();
      location.href = `/static/index.html${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`;
    }),
  );
}
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function meetingStatusLabel(status) {
  return (
    {
      RECRUITING: "모집 중",
      CLOSED: "모집 마감",
      COMPLETED: "완료",
      CANCELED: "취소",
    }[status] ||
    status ||
    "-"
  );
}
function meetingStatusClass(status) {
  return (
    { RECRUITING: "blue", CLOSED: "gray", COMPLETED: "green", CANCELED: "red" }[
      status
    ] || "gray"
  );
}
function approvalTypeLabel(type) {
  return type === "INSTANT" ? "즉시 승인" : "모임장 승인";
}
function skillLevelLabel(level) {
  return (
    {
      BRONZE: "입문",
      SILVER: "초급",
      GOLD: "중급",
      MASTER: "고급",
    }[level] ||
    level ||
    "-"
  );
}
function meetingSkillLevelLabel(level) {
  return level ? skillLevelLabel(level) : "상관없음";
}
function sportVisual(name) {
  const normalizedName = String(name || "").trim();
  const visuals = {
    탁구: { icon: "🏓", theme: "table-tennis" },
    배드민턴: { icon: "🏸", theme: "badminton" },
    테니스: { icon: "🎾", theme: "tennis" },
    풋살: { icon: "⚽", theme: "football" },
    축구: { icon: "⚽", theme: "football" },
    농구: { icon: "🏀", theme: "basketball" },
    야구: { icon: "⚾", theme: "baseball" },
    배구: { icon: "🏐", theme: "volleyball" },
    러닝: { icon: "🏃", theme: "running" },
    런닝: { icon: "🏃", theme: "running" },
  };
  return visuals[normalizedName] || { icon: "🏅", theme: "default" };
}
function formatMeetingDate(value) {
  if (!value) return "-";
  const text = String(value).trim();
  const isoDate = text.match(/^\d{4}-\d{2}-\d{2}/)?.[0];
  if (isoDate) return isoDate;

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return text;

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function formatMeetingTime(value) {
  if (!value) return "-";
  return String(value).slice(0, 5);
}
function queryInt(name) {
  const value = Number(new URLSearchParams(location.search).get(name));
  return Number.isInteger(value) && value > 0 ? value : null;
}
function redirectAfterLogin() {
  const next = new URLSearchParams(location.search).get("next");
  location.href =
    next && next.startsWith("/static/") ? next : "/static/index.html";
}
document.addEventListener("DOMContentLoaded", initializeHeader);
