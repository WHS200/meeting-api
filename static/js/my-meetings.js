const list = document.getElementById("myMeetingList");

async function loadMine() {
  const user = await requireLogin();
  if (!user) return;
  try {
    const data = await apiFetch("/api/meetings/mine");
    document.getElementById("myMeetingTotal").textContent = `${data.total}개`;
    if (!data.meetings.length) {
      list.innerHTML = '<div class="empty">내 모임이 없습니다.</div>';
      return;
    }
    list.innerHTML = data.meetings.map((m) => {
      const sport = sportVisual(m.sport_name);
      const isHost = Number(m.host_id) === Number(user.user_id);
      const actions = isHost
        ? `<span class="badge">내가 만든 모임</span><a class="btn sm" href="detail.html?id=${m.meeting_id}">관리</a><a class="btn sm" href="edit.html?id=${m.meeting_id}">수정</a>`
        : `<span class="badge green">참여 중</span><a class="btn sm" href="detail.html?id=${m.meeting_id}">상세</a>`;
      return `<article class="meeting-card"><div class="thumb sport-${sport.theme}" aria-hidden="true">${sport.icon}</div><div><span class="badge">${escapeHtml(m.sport_name)}</span><h3>${escapeHtml(m.title)}</h3><div class="meta"><span>${formatMeetingDate(m.meeting_date)} · ${formatMeetingTime(m.meeting_time)} ~ ${formatMeetingTime(m.end_time)}</span><span>${escapeHtml(m.location)}</span><span>정원 ${m.max_participants}명</span><span>실력 ${escapeHtml(meetingSkillLevelLabel(m.required_skill_level))}</span></div></div><div class="meeting-side"><span class="badge ${meetingStatusClass(m.status)}">${meetingStatusLabel(m.status)}</span><div class="small-gap">${actions}</div></div></article>`;
    }).join("");
  } catch (e) {
    list.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}

loadMine();
