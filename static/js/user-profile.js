const userId = queryInt("id");
async function loadProfile() {
  const user = await requireLogin();
  if (!user) return;
  if (!userId) {
    document.getElementById("userProfile").innerHTML =
      '<div class="empty">올바른 사용자 번호가 필요합니다.</div>';
    return;
  }
  try {
    const p = await apiFetch(`/api/users/${userId}`);
    document.getElementById("userProfile").innerHTML =
      `<div class="profile-summary"><div class="avatar lg">${p.profile_image ? `<img src="${escapeHtml(p.profile_image)}" alt="프로필">` : escapeHtml((p.nickname || "?").slice(0, 1))}</div><h2>${escapeHtml(p.nickname)}</h2><p class="muted">${escapeHtml(p.region)}</p></div><div class="divider"></div><h2>운동 프로필</h2><div class="sport-list">${(p.sports || []).length ? p.sports.map((s) => `<div class="sport-item"><strong>${escapeHtml(s.sport_name)}</strong><span class="badge">${escapeHtml(s.skill_level)}</span></div>`).join("") : '<div class="empty">등록된 운동 종목이 없습니다.</div>'}</div>`;
  } catch (e) {
    document.getElementById("userProfile").innerHTML =
      `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
loadProfile();
