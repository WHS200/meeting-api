const list = document.getElementById("myMeetingList");
async function loadMine() {
  const user = await requireLogin();
  if (!user) return;
  try {
    const data = await apiFetch("/api/meetings/mine");
    document.getElementById("myMeetingTotal").textContent =
      `총 ${data.total}건`;
    if (!data.meetings.length) {
      list.innerHTML = '<div class="empty">내가 만든 모임이 없습니다.</div>';
      return;
    }
    list.innerHTML = data.meetings
      .map((m) => {
        const sport = sportVisual(m.sport_name);
        return `<article class="meeting-card"><div class="thumb sport-${sport.theme}" aria-hidden="true">${sport.icon}</div><div><span class="badge">${escapeHtml(m.sport_name)}</span><h3>${escapeHtml(m.title)}</h3><div class="meta"><span>${formatMeetingDate(m.meeting_date)} · ${formatMeetingTime(m.meeting_time)}</span><span>${escapeHtml(m.location)}</span><span>정원 ${m.max_participants}명</span><span>실력 ${escapeHtml(meetingSkillLevelLabel(m.required_skill_level))}</span></div></div><div class="meeting-side"><span class="badge ${meetingStatusClass(m.status)}">${meetingStatusLabel(m.status)}</span><div class="small-gap"><a class="btn sm" href="detail.html?id=${m.meeting_id}">관리</a><a class="btn sm" href="edit.html?id=${m.meeting_id}">수정</a></div></div></article>`;
      })
      .join("");
  } catch (e) {
    list.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
loadMine();
