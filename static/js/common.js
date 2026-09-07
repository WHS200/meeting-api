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
  initializeGlobalNavigation(currentUserPromise ? await currentUserPromise.catch(() => null) : null);
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

function initializeGlobalNavigation(user) {
  const header = document.querySelector('.topbar');
  if (!header) return;

  // 모든 화면에서 동일한 핵심 메뉴를 사용한다.
  const mainNav = header.querySelector('.main-nav');
  if (mainNav) {
    const path = location.pathname;
    const links = [
      ['/static/index.html', '모임 찾기', path.endsWith('/index.html') && !path.includes('/admin/')],
      ['/static/create.html', '모임 생성', path.endsWith('/create.html') || path.endsWith('/edit.html')],
      ['/static/my-meetings.html', '내 모임', path.endsWith('/my-meetings.html')],
      ['/static/community.html', '커뮤니티', path.endsWith('/community.html') || path.endsWith('/post-detail.html')],
    ];
    mainNav.innerHTML = links.map(([href, label, active]) =>
      `<a${active ? ' class="active"' : ''} href="${href}">${label}</a>`).join('');
  }

  // 프로필 바로 왼쪽에 친구/알림 바로가기를 둔다.
  let actions = header.querySelector('.top-quick-actions');
  if (!actions) {
    actions = document.createElement('div');
    actions.className = 'top-quick-actions';
    actions.innerHTML = '<a href="/static/friends.html" title="친구" aria-label="친구"><svg class="quick-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3.5 19c.4-3.1 2.2-4.8 5.5-4.8s5.1 1.7 5.5 4.8M14.5 14.8c2.8-.3 4.7 1.1 5 4.2"/></svg></a><a href="/static/notifications.html" title="알림" aria-label="알림"><svg class="quick-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 8.5h18C21 16 18 16 18 9Z"/><path d="M10 20h4"/></svg></a><a href="/static/chat.html" title="채팅" aria-label="채팅"><svg class="quick-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 8.8 8.8 0 0 1-3.5-.7L4 20l1.4-3.4A7.3 7.3 0 0 1 4 11.5 7.5 7.5 0 0 1 12 4a7.5 7.5 0 0 1 8 7.5Z"/><path d="M8 11.5h.01M12 11.5h.01M16 11.5h.01"/></svg></a>';
    const topActions = header.querySelector('.top-actions');
    if (topActions) {
      const profile = [...topActions.querySelectorAll('a')].find((a) => /profile\.html/.test(a.getAttribute('href') || ''));
      if (profile) topActions.insertBefore(actions, profile);
      else topActions.append(actions);
    }
    else {
      const profile = [...header.querySelectorAll('a')].find((a) => /profile\.html/.test(a.getAttribute('href') || ''));
      if (profile) profile.parentElement.insertBefore(actions, profile);
      else header.querySelector('.topbar-inner')?.append(actions);
    }
  }

  // 관리자 링크는 서버가 알려준 role이 ADMIN인 경우에만 표시한다.
  const existingAdmin = header.querySelector('[data-admin-nav]');
  if (user?.role === 'ADMIN' && !existingAdmin) {
    const admin = document.createElement('a');
    admin.href = '/static/admin/index.html';
    admin.textContent = '관리자';
    admin.dataset.adminNav = 'true';
    mainNav?.append(admin);
  } else if (user?.role !== 'ADMIN' && existingAdmin) {
    existingAdmin.remove();
  }
}
