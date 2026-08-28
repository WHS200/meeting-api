const form = document.getElementById("meetingForm");
const formStatus = document.getElementById("formStatus");
const editId = queryInt("id");
async function loadSportOptions() {
  const sports = await apiFetch("/api/sports");
  form.sport_id.innerHTML = sports
    .map(
      (s) =>
        `<option value="${s.sport_id}">${escapeHtml(s.sport_name)}</option>`,
    )
    .join("");
  if (!sports.length) {
    form.sport_id.innerHTML =
      "<option selected disabled>활성 종목 없음</option>";
    form.querySelector("button[type=submit]").disabled = true;
  }
}
async function loadForEdit() {
  if (!editId) return;
  const m = await apiFetch(`/api/meetings/${editId}`);
  form.title.value = m.title;
  form.description.value = m.description;
  form.sport_id.value = m.sport_id;
  form.meeting_date.value = formatMeetingDate(m.meeting_date);
  form.meeting_time.value = formatMeetingTime(m.meeting_time);
  form.location.value = m.location;
  form.max_participants.value = m.max_participants;
  form.required_skill_level.value = m.required_skill_level || "";
  form.approval_type.value = m.approval_type;
  form.status.value = m.status;
  document.querySelector("[data-form-title]").textContent = "모임 수정";
  document.querySelector("[data-submit-label]").textContent = "수정 저장";
  document.getElementById("statusField").hidden = false;
}
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setStatus(formStatus, "저장 중...");
  const body = {
    title: form.title.value,
    description: form.description.value,
    sport_id: Number(form.sport_id.value),
    meeting_date: form.meeting_date.value,
    meeting_time: form.meeting_time.value,
    location: form.location.value,
    max_participants: Number(form.max_participants.value),
    required_skill_level: form.required_skill_level.value || null,
    approval_type: form.approval_type.value,
  };
  if (editId) body.status = form.status.value;
  try {
    const data = await apiFetch(
      editId ? `/api/meetings/${editId}` : "/api/meetings",
      { method: editId ? "PUT" : "POST", body: JSON.stringify(body) },
    );
    setStatus(formStatus, data.message || "저장 완료", "success");
    const id = editId || data.meeting_id;
    setTimeout(() => (location.href = `/static/detail.html?id=${id}`), 300);
  } catch (error) {
    setStatus(formStatus, error.message, "error");
  }
});
(async () => {
  const user = await requireLogin();
  if (!user) return;
  try {
    await loadSportOptions();
    await loadForEdit();
  } catch (error) {
    setStatus(formStatus, error.message, "error");
  }
})();
