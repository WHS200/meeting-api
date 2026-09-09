const form = document.getElementById("meetingForm");
const formStatus = document.getElementById("formStatus");
const editId = queryInt("id");
const TIME_STEP_MINUTES = 15;
const TIME_MAX_INDEX = 95;
const MIN_DURATION_STEPS = 2;
const MAX_DURATION_STEPS = 48;
const timeRange = (() => {
  const root = document.querySelector("[data-time-range]");
  if (!root) return null;
  const start = root.querySelector("[data-start-range]");
  const end = root.querySelector("[data-end-range]");
  const fill = root.querySelector(".time-range-fill");
  const summary = root.querySelector("[data-time-summary]");
  const toMinutes = (value) => {
    const [hours, minutes] = String(value || "").split(":").map(Number);
    return Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : null;
  };
  const toValue = (index) => {
    const minutes = index * TIME_STEP_MINUTES;
    return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
  };
  const display = (index) => {
    const minutes = index * TIME_STEP_MINUTES;
    const hours = Math.floor(minutes / 60);
    const period = hours < 12 ? "오전" : "오후";
    return `${period} ${hours % 12 || 12}:${String(minutes % 60).padStart(2, "0")}`;
  };
  function update(nextStart, nextEnd, changed) {
    let startValue = Math.round(Number(nextStart));
    let endValue = Math.round(Number(nextEnd));
    if (changed === "start") {
      startValue = Math.min(startValue, endValue - MIN_DURATION_STEPS);
      startValue = Math.max(startValue, endValue - MAX_DURATION_STEPS);
    } else {
      endValue = Math.max(endValue, startValue + MIN_DURATION_STEPS);
      endValue = Math.min(endValue, startValue + MAX_DURATION_STEPS);
    }
    startValue = Math.max(0, Math.min(startValue, TIME_MAX_INDEX - MIN_DURATION_STEPS));
    endValue = Math.max(startValue + MIN_DURATION_STEPS, Math.min(endValue, TIME_MAX_INDEX));
    if (endValue - startValue > MAX_DURATION_STEPS) {
      if (changed === "start") startValue = endValue - MAX_DURATION_STEPS;
      else endValue = startValue + MAX_DURATION_STEPS;
    }
    start.value = startValue;
    end.value = endValue;
    form.meeting_time.value = toValue(startValue);
    form.end_time.value = toValue(endValue);
    summary.textContent = `${display(startValue)} - ${display(endValue)}`;
    const startPct = (startValue / TIME_MAX_INDEX) * 100;
    const endPct = (endValue / TIME_MAX_INDEX) * 100;
    fill.style.left = `${startPct}%`;
    fill.style.width = `${endPct - startPct}%`;
  }
  start.addEventListener("input", () => update(start.value, end.value, "start"));
  end.addEventListener("input", () => update(start.value, end.value, "end"));
  return {
    setValues(startValue, endValue) {
      const startIndex = Math.max(0, Math.min(TIME_MAX_INDEX, Math.round((toMinutes(startValue) ?? 1080) / TIME_STEP_MINUTES)));
      const endIndex = Math.max(0, Math.min(TIME_MAX_INDEX, Math.round((toMinutes(endValue) ?? 1140) / TIME_STEP_MINUTES)));
      update(startIndex, endIndex, "end");
    },
  };
})();
timeRange?.setValues("18:00", "19:00");
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
  timeRange?.setValues(formatMeetingTime(m.meeting_time), formatMeetingTime(m.end_time));
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
    end_time: form.end_time.value,
    location: form.location.value,
    max_participants: Number(form.max_participants.value),
    required_skill_level: form.required_skill_level.value || null,
    approval_type: form.approval_type.value,
  };
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
