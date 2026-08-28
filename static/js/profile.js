const SKILL_LEVELS = ["BRONZE", "SILVER", "GOLD", "MASTER"];
let me = null,
  sports = [],
  mySports = [];
const avatar = document.getElementById("avatar"),
  sportList = document.getElementById("sportList"),
  sportSelect = document.getElementById("sportSelect");
async function loadMe() {
  try {
    me = await apiFetch("/api/users/me");
    document.getElementById("nicknameText").textContent = me.nickname;
    document.getElementById("regionText").textContent = me.region;
    document.getElementById("loginIdText").textContent = me.login_id;
    document.getElementById("emailText").textContent = me.email;
    document.getElementById("birthText").textContent = formatMeetingDate(
      me.birth_date,
    );
    document.getElementById("genderText").textContent = me.gender;
    document.getElementById("nicknameInput").value = me.nickname;
    document.getElementById("regionInput").value = me.region;
    avatar.innerHTML = me.profile_image
      ? `<img src="${escapeHtml(me.profile_image)}" alt="프로필 이미지">`
      : escapeHtml((me.nickname || "?").slice(0, 1));
  } catch (e) {
    if (e.status === 401) {
      location.href = "/static/login.html";
      return;
    }
    showToast(e.message);
  }
}
async function loadSports() {
  try {
    sports = await apiFetch("/api/sports");
    sportSelect.innerHTML = sports.length
      ? sports
          .map(
            (s) =>
              `<option value="${s.sport_id}">${escapeHtml(s.sport_name)}</option>`,
          )
          .join("")
      : "<option disabled selected>활성 종목 없음</option>";
  } catch (e) {
    showToast(e.message);
  }
}
async function loadMySports() {
  try {
    const d = await apiFetch("/api/users/me/sports");
    mySports = d.sports || [];
    renderMySports();
  } catch (e) {
    showToast(e.message);
  }
}
function renderMySports() {
  sportList.innerHTML = mySports.length
    ? mySports
        .map(
          (s) =>
            `<div class="sport-item"><div><strong>${escapeHtml(s.sport_name)}</strong><small>현재 실력 ${escapeHtml(skillLevelLabel(s.skill_level))}</small></div><div class="actions"><select data-level="${s.sport_id}">${SKILL_LEVELS.map((v) => `<option value="${v}" ${v === s.skill_level ? "selected" : ""}>${escapeHtml(skillLevelLabel(v))}</option>`).join("")}</select><button class="btn sm" data-update-sport="${s.sport_id}">수정</button><button class="btn sm danger" data-delete-sport="${s.sport_id}" data-name="${escapeHtml(s.sport_name)}">삭제</button></div></div>`,
        )
        .join("")
    : '<div class="empty">등록된 운동 종목이 없습니다.</div>';
  document
    .querySelectorAll("[data-update-sport]")
    .forEach(
      (b) => (b.onclick = () => updateSport(Number(b.dataset.updateSport))),
    );
  document
    .querySelectorAll("[data-delete-sport]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          deleteSport(Number(b.dataset.deleteSport), b.dataset.name)),
    );
}
async function updateSport(id) {
  const level = document.querySelector(`[data-level="${id}"]`).value;
  try {
    const d = await apiFetch(`/api/users/me/sports/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ skill_level: level }),
    });
    showToast(d.message);
    await loadMySports();
  } catch (e) {
    showToast(e.message);
  }
}
async function deleteSport(id, name) {
  if (!confirm(`${name} 종목을 삭제할까요?`)) return;
  try {
    const d = await apiFetch(`/api/users/me/sports/${id}`, {
      method: "DELETE",
    });
    showToast(d.message);
    await loadMySports();
  } catch (e) {
    showToast(e.message);
  }
}
document.getElementById("profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const d = await apiFetch("/api/users/me", {
      method: "PATCH",
      body: JSON.stringify({
        nickname: e.currentTarget.nickname.value,
        region: e.currentTarget.region.value,
      }),
    });
    showToast(d.message);
    currentUserPromise = null;
    await loadMe();
  } catch (err) {
    showToast(err.message);
  }
});
document.getElementById("sportForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!sports.length) return showToast("활성 종목이 없습니다.");
  try {
    const d = await apiFetch("/api/users/me/sports", {
      method: "POST",
      body: JSON.stringify({
        sport_id: Number(e.currentTarget.sport_id.value),
        skill_level: e.currentTarget.skill_level.value,
      }),
    });
    showToast(d.message);
    await loadMySports();
  } catch (err) {
    showToast(err.message);
  }
});
document.getElementById("imageForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = e.currentTarget.profile_image.files[0];
  if (!file) return showToast("이미지 파일을 선택하세요.");
  const fd = new FormData();
  fd.append("profile_image", file);
  try {
    const d = await apiFetch("/api/users/me/profile-image", {
      method: "POST",
      body: fd,
    });
    showToast(d.message);
    await loadMe();
  } catch (err) {
    showToast(err.message);
  }
});
document
  .getElementById("passwordForm")
  .addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const d = await apiFetch("/api/users/me/password", {
        method: "PATCH",
        body: JSON.stringify({
          current_password: e.currentTarget.current_password.value,
          new_password: e.currentTarget.new_password.value,
        }),
      });
      showToast(d.message);
      e.currentTarget.reset();
    } catch (err) {
      showToast(err.message);
    }
  });
document.getElementById("deleteButton").addEventListener("click", async () => {
  if (!confirm("계정을 삭제할까요?")) return;
  try {
    const d = await apiFetch("/api/users/me", { method: "DELETE" });
    alert(d.message);
    location.href = "/static/login.html";
  } catch (e) {
    showToast(e.message);
  }
});
(async () => {
  const user = await requireLogin();
  if (!user) return;
  await Promise.all([loadMe(), loadSports(), loadMySports()]);
})();
