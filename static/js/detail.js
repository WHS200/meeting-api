const meetingId = queryInt("id");
let meeting = null;
let isHost = false;
const content = document.getElementById("detailContent");
const side = document.getElementById("detailSide");
const hostPanel = document.getElementById("hostPanel");
async function loadDetail() {
  if (!meetingId) {
    content.innerHTML =
      '<div class="empty">올바른 meeting id가 필요합니다.</div>';
    return;
  }
  try {
    meeting = await apiFetch(`/api/meetings/${meetingId}`);
    renderDetail();
    const user = await getCurrentUser();
    if (user) await detectHostAndLoad();
    else renderGuestActions();
  } catch (e) {
    content.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
function renderDetail() {
  content.innerHTML = `<div class="detail-title"><div><span class="badge">${escapeHtml(meeting.sport_name)}</span><h1>${escapeHtml(meeting.title)}</h1><span class="badge ${meetingStatusClass(meeting.status)}">${meetingStatusLabel(meeting.status)}</span></div></div><div class="info-grid"><div class="info-item"><small>날짜</small><strong>${formatMeetingDate(meeting.meeting_date)}</strong></div><div class="info-item"><small>시간</small><strong>${formatMeetingTime(meeting.meeting_time)}</strong></div><div class="info-item"><small>장소</small><strong>${escapeHtml(meeting.location)}</strong></div><div class="info-item"><small>정원</small><strong>${meeting.max_participants}명 (모임장 포함)</strong></div><div class="info-item"><small>승인 방식</small><strong>${approvalTypeLabel(meeting.approval_type)}</strong></div><div class="info-item"><small>상태</small><strong>${meetingStatusLabel(meeting.status)}</strong></div></div><div class="description">${escapeHtml(meeting.description)}</div><div class="host-box"><div class="avatar">${escapeHtml((meeting.host_name || "?").slice(0, 1))}</div><div class="grow"><strong>${escapeHtml(meeting.host_name)}</strong><div class="subtle">모임장</div></div></div>`;
}
function renderGuestActions() {
  side.innerHTML =
    '<h2>참가</h2><p class="muted">참가 신청과 채팅은 로그인이 필요합니다.</p><a class="btn blue block" href="login.html">로그인</a>';
}
async function detectHostAndLoad() {
  try {
    const pending = await apiFetch(`/api/meetings/${meetingId}/participants`);
    isHost = true;
    renderHostActions();
    await loadHostManagement(pending.participants || []);
  } catch (error) {
    if (error.status === 403) {
      renderParticipantActions();
      await loadApprovedPublic();
    } else {
      showToast(error.message);
      renderParticipantActions();
    }
  }
}
function renderParticipantActions() {
  const recruiting = meeting.status === "RECRUITING";
  side.innerHTML = `<h2>참가</h2><p class="muted">현재 API에는 내 신청 상태 조회가 없어 신청/취소 버튼을 함께 제공합니다. 서버가 실제 상태를 검증합니다.</p><div class="action-stack"><button id="joinButton" class="btn blue" ${recruiting ? "" : "disabled"}>${recruiting ? "참가 신청" : "모집 중이 아님"}</button><button id="cancelButton" class="btn danger">참가 취소</button><a class="btn" href="chat.html">채팅방 보기</a></div>`;
  document.getElementById("joinButton").onclick = joinMeeting;
  document.getElementById("cancelButton").onclick = cancelMeeting;
}
function renderHostActions() {
  side.innerHTML = `<h2>모임장 관리</h2><div class="action-stack"><a class="btn" href="edit.html?id=${meetingId}">모임 수정</a><a class="btn" href="chat.html">채팅방 보기</a><button id="deleteMeeting" class="btn danger">모임 삭제</button></div>`;
  document.getElementById("deleteMeeting").onclick = deleteMeeting;
}
async function joinMeeting() {
  try {
    const d = await apiFetch(`/api/meetings/${meetingId}/participants`, {
      method: "POST",
    });
    showToast(`${d.message} (${d.participation_status})`);
  } catch (e) {
    showToast(e.message);
  }
}
async function cancelMeeting() {
  if (!confirm("참가 신청/참여를 취소할까요?")) return;
  try {
    const d = await apiFetch(`/api/meetings/${meetingId}/participants/me`, {
      method: "DELETE",
    });
    showToast(d.message);
  } catch (e) {
    showToast(e.message);
  }
}
async function deleteMeeting() {
  if (!confirm("모임을 삭제할까요?")) return;
  try {
    await apiFetch(`/api/meetings/${meetingId}`, { method: "DELETE" });
    location.href = "/static/my-meetings.html";
  } catch (e) {
    showToast(e.message);
  }
}
async function loadApprovedPublic() {
  try {
    const d = await apiFetch(
      `/api/meetings/${meetingId}/participants/approved`,
    );
    document.getElementById("approvedSummary").textContent =
      `승인된 참가자 ${d.participants.length}명`;
  } catch (e) {
    if (e.status !== 401) showToast(e.message);
  }
}
async function profileFor(userId) {
  try {
    return await apiFetch(`/api/users/${userId}`);
  } catch {
    return null;
  }
}
async function loadHostManagement(pending) {
  hostPanel.hidden = false;
  const pendingBody = document.getElementById("pendingBody");
  pendingBody.innerHTML = pending.length
    ? pending
        .map(
          (p) =>
            `<tr><td>${p.user_id}</td><td>${escapeHtml(p.nickname)}</td><td>${escapeHtml(p.participation_status)}</td><td><div class="small-gap"><button class="btn sm blue" data-approve="${p.user_id}">승인</button><button class="btn sm danger" data-reject="${p.user_id}">거절</button><a class="btn sm" href="user-profile.html?id=${p.user_id}">프로필</a></div></td></tr>`,
        )
        .join("")
    : '<tr><td colspan="4">승인 대기 신청이 없습니다.</td></tr>';
  pendingBody
    .querySelectorAll("[data-approve]")
    .forEach((b) => (b.onclick = () => approve(Number(b.dataset.approve))));
  pendingBody
    .querySelectorAll("[data-reject]")
    .forEach((b) => (b.onclick = () => reject(Number(b.dataset.reject))));
  await loadApprovedHost();
}
async function loadApprovedHost() {
  const d = await apiFetch(`/api/meetings/${meetingId}/participants/approved`);
  const rows = await Promise.all(
    d.participants.map(async (p) => ({
      p,
      profile: await profileFor(p.user_id),
    })),
  );
  document.getElementById("approvedBody").innerHTML = rows.length
    ? rows
        .map(
          ({ p, profile }) =>
            `<tr><td>${p.user_id}</td><td>${escapeHtml(profile?.nickname || "-")}</td><td>${escapeHtml(p.attendance_status || "-")}</td><td><div class="small-gap"><button class="btn sm" data-attend="${p.user_id}" data-value="ATTENDED">출석</button><button class="btn sm" data-attend="${p.user_id}" data-value="NO_SHOW">노쇼</button><button class="btn sm danger" data-kick="${p.user_id}">강퇴</button><a class="btn sm" href="user-profile.html?id=${p.user_id}">프로필</a></div></td></tr>`,
        )
        .join("")
    : '<tr><td colspan="4">승인된 참가자가 없습니다.</td></tr>';
  document
    .querySelectorAll("[data-attend]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          attendance(Number(b.dataset.attend), b.dataset.value)),
    );
  document
    .querySelectorAll("[data-kick]")
    .forEach((b) => (b.onclick = () => kick(Number(b.dataset.kick))));
}
async function approve(id) {
  try {
    const d = await apiFetch(
      `/api/meetings/${meetingId}/participants/${id}/approve`,
      { method: "POST" },
    );
    showToast(d.message);
    await detectHostAndLoad();
  } catch (e) {
    showToast(e.message);
  }
}
async function reject(id) {
  try {
    const d = await apiFetch(
      `/api/meetings/${meetingId}/participants/${id}/reject`,
      { method: "POST" },
    );
    showToast(d.message);
    await detectHostAndLoad();
  } catch (e) {
    showToast(e.message);
  }
}
async function kick(id) {
  if (!confirm("이 참가자를 강퇴할까요?")) return;
  try {
    const d = await apiFetch(`/api/meetings/${meetingId}/participants/${id}`, {
      method: "DELETE",
    });
    showToast(d.message);
    await detectHostAndLoad();
  } catch (e) {
    showToast(e.message);
  }
}
async function attendance(id, value) {
  try {
    const d = await apiFetch(
      `/api/meetings/${meetingId}/participants/${id}/attendance`,
      { method: "POST", body: JSON.stringify({ attendance_status: value }) },
    );
    showToast(d.message);
    await loadApprovedHost();
  } catch (e) {
    showToast(e.message);
  }
}
loadDetail();
