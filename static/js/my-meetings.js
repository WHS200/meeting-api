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
    const statusPriority = { RECRUITING: 1, CLOSED: 2, COMPLETED: 3, CANCELED: 4 };
    const meetings = data.meetings.map((meeting, index) => ({ meeting, index })).sort((a, b) =>
      (statusPriority[a.meeting.status] || 5) - (statusPriority[b.meeting.status] || 5) || a.index - b.index
    ).map(({ meeting }) => meeting);
    list.innerHTML = meetings.map((m) => {
      const sport = sportVisual(m.sport_name);
      const isHost = Number(m.host_id) === Number(user.user_id);
      const participationLabels = { HOST: "내가 만든 모임", APPROVED: "참여 확정", PENDING: "승인 대기", WAITING: "대기열" };
      const participationClass = m.my_participation_status === "APPROVED" ? "green" : "";
      const actions = isHost
        ? `<span class="badge">${participationLabels.HOST}</span><a class="btn sm" href="detail.html?id=${m.meeting_id}">관리</a><a class="btn sm" href="edit.html?id=${m.meeting_id}">수정</a>`
        : `<span class="badge ${participationClass}">${participationLabels[m.my_participation_status] || "참여 중"}</span><a class="btn sm" href="detail.html?id=${m.meeting_id}">상세</a>`;
      const archivedClass = m.status === "COMPLETED" || m.status === "CANCELED" ? " archived" : "";
      return `<article class="meeting-card${archivedClass}"><div class="thumb sport-${sport.theme}" aria-hidden="true">${sport.icon}</div><div><span class="badge">${escapeHtml(m.sport_name)}</span><h3>${escapeHtml(m.title)}</h3><div class="meta"><span>${formatMeetingDate(m.meeting_date)} · ${formatMeetingTime(m.meeting_time)} ~ ${formatMeetingTime(m.end_time)}</span><span>${escapeHtml(m.location)}</span><span>정원 ${m.max_participants}명</span><span>실력 ${escapeHtml(meetingSkillLevelLabel(m.required_skill_level))}</span></div></div><div class="meeting-side"><span class="badge ${meetingStatusClass(m.status)}">${meetingStatusLabel(m.status)}</span><div class="small-gap">${actions}</div></div></article>`;
    }).join("");
    list.querySelectorAll(".meeting-card").forEach((card, index) => {
      const meeting = meetings[index];
      const meta = card.querySelector(".meta");
      if (meta && meeting) meta.insertAdjacentHTML("beforeend", `<span>참여 ${meeting.participant_count || 1} / ${meeting.max_participants}명</span><span>남은 자리 ${meeting.remaining_slots ?? 0}명</span>`);
    });
  } catch (e) {
    list.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}

loadMine();
