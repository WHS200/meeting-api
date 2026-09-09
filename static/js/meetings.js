let sportsCache = [];
const filterForm = document.getElementById("filterForm");
const meetingList = document.getElementById("meetingList");
const totalText = document.getElementById("meetingTotal");
let currentPage = Number(new URLSearchParams(location.search).get("page") || 1);
const pageSize = 20;
const pagination = document.createElement("div");
pagination.className = "feature-row meeting-pagination";
pagination.innerHTML = '<button type="button" class="btn sm" id="previousPage">이전</button><strong id="pageIndicator" class="grow" style="text-align:center"></strong><button type="button" class="btn sm" id="nextPage">다음</button>';
meetingList.insertAdjacentElement("afterend", pagination);
const previousPage = pagination.querySelector("#previousPage");
const nextPage = pagination.querySelector("#nextPage");
const pageIndicator = pagination.querySelector("#pageIndicator");
async function loadSports() {
  try {
    sportsCache = await apiFetch("/api/sports");
    const select = filterForm.sport_id;
    select.innerHTML =
      '<option value="">전체 종목</option>' +
      sportsCache
        .map(
          (s) =>
            `<option value="${s.sport_id}">${escapeHtml(s.sport_name)}</option>`,
        )
        .join("");
    const q = new URLSearchParams(location.search);
    select.value = q.get("sport_id") || "";
  } catch (e) {
    showToast(e.message);
  }
}
function buildQuery() {
  const p = new URLSearchParams();
  for (const name of ["keyword", "sport_id", "date", "location", "status"]) {
    const v = filterForm[name].value.trim();
    if (v) p.set(name, v);
  }
  return p;
}
async function loadMeetings() {
  meetingList.innerHTML = '<div class="empty">모임을 불러오는 중...</div>';
  const p = buildQuery();
  p.set("page", currentPage);
  p.set("size", pageSize);
  history.replaceState(
    null,
    "",
    `${location.pathname}${p.toString() ? `?${p}` : ""}`,
  );
  try {
    const data = await apiFetch(`/api/meetings${p.toString() ? `?${p}` : ""}`);
    totalText.textContent = `총 ${data.total}건`;
    renderMeetings(data.meetings || []);
    pageIndicator.textContent = `${data.page || currentPage} / ${data.total_pages || 1}`;
    previousPage.disabled = currentPage <= 1;
    nextPage.disabled = currentPage >= (data.total_pages || 1);
    pagination.hidden = (data.total_pages || 1) <= 1;
  } catch (e) {
    meetingList.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
function renderMeetings(items) {
  if (!items.length) {
    meetingList.innerHTML =
      '<div class="empty">조건에 맞는 모임이 없습니다.</div>';
    return;
  }
  meetingList.innerHTML = items
    .map((m) => {
      const sport = sportVisual(m.sport_name);
      return `<a class="meeting-card" href="detail.html?id=${m.meeting_id}"><div class="thumb sport-${sport.theme}" aria-hidden="true">${sport.icon}</div><div><span class="badge">${escapeHtml(m.sport_name)}</span><h3>${escapeHtml(m.title)}</h3><div class="meta"><span>◷ ${formatMeetingDate(m.meeting_date)} · ${formatMeetingTime(m.meeting_time)} ~ ${formatMeetingTime(m.end_time)}</span><span>⌖ ${escapeHtml(m.location)}</span></div><div class="meta"><span>모임장 ${escapeHtml(m.host_name)}</span><span>정원 ${m.max_participants}명</span><span>실력 ${escapeHtml(meetingSkillLevelLabel(m.required_skill_level))}</span><span>${approvalTypeLabel(m.approval_type)}</span></div></div><div class="meeting-side"><span class="badge ${meetingStatusClass(m.status)}">${meetingStatusLabel(m.status)}</span></div></a>`;
    })
    .join("");
  meetingList.querySelectorAll(".meeting-card").forEach((card, index) => {
    const meeting = items[index];
    const meta = card.querySelectorAll(".meta")[1];
    if (meta && meeting) {
      meta.insertAdjacentHTML("beforeend", `<span>참여 ${meeting.participant_count || 1} / ${meeting.max_participants}명</span><span>남은 자리 ${meeting.remaining_slots ?? 0}명</span>`);
    }
  });
}
filterForm.addEventListener("submit", (e) => {
  e.preventDefault();
  currentPage = 1;
  loadMeetings();
});
document.getElementById("resetFilters").addEventListener("click", () => {
  filterForm.reset();
  currentPage = 1;
  loadMeetings();
});
previousPage.addEventListener("click", () => { if (currentPage > 1) { currentPage -= 1; loadMeetings(); } });
nextPage.addEventListener("click", () => { currentPage += 1; loadMeetings(); });
(async () => {
  const q = new URLSearchParams(location.search);
  for (const name of ["keyword", "date", "location", "status"])
    if (q.get(name)) filterForm[name].value = q.get(name);
  await loadSports();
  await loadMeetings();
})();
