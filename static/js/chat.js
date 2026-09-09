let socket = null, currentRoom = null, me = null;
const meetingRoomList = document.getElementById("meetingRoomList");
const directRoomList = document.getElementById("directRoomList");
const meetingRoomMore = document.getElementById("meetingRoomMore");
const directRoomMore = document.getElementById("directRoomMore");
const messagesEl = document.getElementById("messages");
const roomTitle = document.getElementById("roomTitle");
const roomStatus = document.getElementById("roomStatus");
const leaveRoomButton = document.getElementById("leaveRoomButton");
const memberList = document.getElementById("memberList");
const messageForm = document.getElementById("messageForm");
const renderedMessageIds = new Set();
let nextBeforeMessageId = null;
let loadedRooms = [];
const roomExpanded = { meeting: false, direct: false };
const meetingStatusLabels = { RECRUITING: "모집 중", CLOSED: "모집 마감", COMPLETED: "완료", CANCELED: "취소" };
const meetingStatusPriority = { RECRUITING: 1, CLOSED: 2, COMPLETED: 3, CANCELED: 4 };
const olderMessagesButton = document.createElement("button");
olderMessagesButton.type = "button";
olderMessagesButton.className = "btn sm";
olderMessagesButton.textContent = "이전 메시지 불러오기";
olderMessagesButton.hidden = true;
messagesEl.parentElement.insertBefore(olderMessagesButton, messagesEl);

async function startChat() {
  me = await requireLogin();
  if (!me) return;
  if (typeof io !== "function") return showToast("채팅 기능을 불러오지 못했습니다.");
  socket = io();
  socket.on("connect_error", (e) => showToast(e.message));
  socket.on("error", (d) => showToast(d?.message || "채팅 오류"));
  socket.on("receive_message", (m) => {
    if (currentRoom && Number(m.chat_room_id) === Number(currentRoom.chat_room_id)) {
      const shouldStick = isNearBottom();
      appendMessage(m);
      if (shouldStick) scrollBottom();
    }
  });
  await loadRooms();
}

function roomButton(room) {
  const title = room.meeting_title || room.direct_nickname || (room.room_type === "DIRECT" ? `개인 채팅 #${room.chat_room_id}` : `모임 채팅방 #${room.chat_room_id}`);
  const avatar = room.direct_profile_image
    ? `<img src="${escapeHtml(room.direct_profile_image)}" alt="">`
    : escapeHtml((room.meeting_title || room.direct_nickname || "채").slice(0, 1));
  const status = room.room_type !== "DIRECT" && meetingStatusLabels[room.meeting_status]
    ? `<span class="chat-status-badge status-${String(room.meeting_status).toLowerCase()}">${meetingStatusLabels[room.meeting_status]}</span>` : "";
  const archived = room.room_type !== "DIRECT" && ["COMPLETED", "CANCELED"].includes(room.meeting_status) ? " archived" : "";
  const titleMarkup = room.room_type !== "DIRECT" && room.meeting_id
    ? `<span class="chat-room-title" data-meeting-link="${room.meeting_id}" role="link" tabindex="0">${escapeHtml(title)}</span>`
    : `<span class="chat-room-title">${escapeHtml(title)}</span>`;
  return `<button class="chat-room${archived}" data-room="${room.chat_room_id}"><div class="avatar">${avatar}</div><div class="grow">${titleMarkup}${status}</div></button>`;
}

function renderRoomGroup(list, rooms, moreButton, key) {
  const visible = roomExpanded[key] ? rooms : rooms.slice(0, 4);
  list.innerHTML = rooms.length ? visible.map(roomButton).join("") : `<div class="empty">${key === "meeting" ? "모임 채팅방이 없습니다." : "개인 채팅방이 없습니다."}</div>`;
  moreButton.hidden = rooms.length <= 4;
  moreButton.textContent = roomExpanded[key] ? "접기" : "더보기";
  moreButton.parentElement.classList.toggle("expanded", roomExpanded[key]);
}

function bindRoomButtons() {
  document.querySelectorAll("[data-room]").forEach((button) => {
    button.onclick = () => openRoom(loadedRooms.find((r) => r.chat_room_id === Number(button.dataset.room)));
    const titleLink = button.querySelector("[data-meeting-link]");
    if (titleLink) {
      const goToMeeting = (event) => { event.stopPropagation(); location.href = `/static/detail.html?id=${Number(titleLink.dataset.meetingLink)}`; };
      titleLink.onclick = goToMeeting;
      titleLink.onkeydown = (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); goToMeeting(event); } };
    }
  });
}

function sortedMeetingRooms(rooms) {
  return rooms.sort((a, b) => (meetingStatusPriority[a.meeting_status] || 5) - (meetingStatusPriority[b.meeting_status] || 5));
}

async function loadRooms() {
  try {
    const d = await apiFetch("/api/chat/rooms");
    const rooms = d.chat_rooms || [];
    loadedRooms = rooms;
    const meetingRooms = sortedMeetingRooms(rooms.filter((r) => r.room_type !== "DIRECT"));
    const directRooms = rooms.filter((r) => r.room_type === "DIRECT");
    renderRoomGroup(meetingRoomList, meetingRooms, meetingRoomMore, "meeting");
    renderRoomGroup(directRoomList, directRooms, directRoomMore, "direct");
    bindRoomButtons();
    await openRoom(rooms.find((r) => r.chat_room_id === queryInt("room")) || rooms[0]);
  } catch (e) {
    meetingRoomList.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
    directRoomList.innerHTML = "";
  }
}

async function openRoom(room) {
  if (!room) return;
  if (currentRoom) socket.emit("leave_room", { chat_room_id: currentRoom.chat_room_id });
  currentRoom = room;
  renderedMessageIds.clear();
  nextBeforeMessageId = null;
  olderMessagesButton.hidden = true;
  document.querySelectorAll("[data-room]").forEach((b) => b.classList.toggle("active", Number(b.dataset.room) === room.chat_room_id));
  roomTitle.textContent = room.meeting_title || room.direct_nickname || "개인 채팅";
  if (room.room_type !== "DIRECT" && room.meeting_id) {
    roomTitle.href = `/static/detail.html?id=${Number(room.meeting_id)}`;
    roomTitle.classList.add("is-link");
  } else {
    roomTitle.removeAttribute("href");
    roomTitle.classList.remove("is-link");
  }
  const statusLabel = room.room_type !== "DIRECT" ? meetingStatusLabels[room.meeting_status] : "";
  roomStatus.hidden = !statusLabel;
  roomStatus.textContent = statusLabel || "";
  roomStatus.className = statusLabel ? `chat-status-badge status-${String(room.meeting_status).toLowerCase()}` : "chat-status-badge";
  const canLeave = room.room_type !== "DIRECT" && ["RECRUITING", "CLOSED"].includes(room.meeting_status)
    && Number(room.meeting_host_id) !== Number(me.user_id);
  leaveRoomButton.hidden = !canLeave;
  messagesEl.innerHTML = '<div class="empty">메시지를 불러오는 중...</div>';
  socket.emit("join_room", { chat_room_id: room.chat_room_id });
  try {
    const [m, mem] = await Promise.all([
      apiFetch(`/api/chat/rooms/${room.chat_room_id}/messages`),
      apiFetch(`/api/chat/rooms/${room.chat_room_id}/members`),
    ]);
    messagesEl.innerHTML = "";
    (m.messages || []).forEach((message) => appendMessage(message));
    nextBeforeMessageId = m.next_before_message_id;
    olderMessagesButton.hidden = !m.has_more;
    renderMembers(mem.members || []);
    scrollBottom();
  } catch (e) {
    messagesEl.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}

function renderMembers(members) {
  memberList.innerHTML = members.map((m) => `<span class="member-pill">${escapeHtml(m.nickname)}</span>`).join("");
}
function appendMessage(m, prepend = false) {
  if (renderedMessageIds.has(Number(m.message_id))) return;
  renderedMessageIds.add(Number(m.message_id));
  const mine = m.sender_nickname === me.nickname;
  const senderName = m.sender_nickname || `사용자 ${m.sender_id}`;
  const senderId = Number(m.sender_id);
  const avatarContent = m.sender_profile_image ? `<img src="${escapeHtml(m.sender_profile_image)}" alt="${escapeHtml(senderName)} 프로필">` : escapeHtml(senderName.slice(0, 1));
  const avatar = mine ? "" : `<a class="avatar chat-profile-avatar" href="user-profile.html?id=${senderId}" aria-label="${escapeHtml(senderName)} 프로필 보기">${avatarContent}</a>`;
  const div = document.createElement("div");
  div.className = `message ${mine ? "mine" : ""}`;
  div.innerHTML = `${avatar}<div class="bubble"><strong>${escapeHtml(senderName)}</strong><div>${escapeHtml(m.content)}</div><div class="message-meta">${escapeHtml(String(m.created_at || "").replace("T", " "))}</div></div>`;
  if (prepend) messagesEl.prepend(div);
  else messagesEl.appendChild(div);
}
olderMessagesButton.onclick = async () => {
  if (!currentRoom || !nextBeforeMessageId) return;
  olderMessagesButton.disabled = true;
  const previousHeight = messagesEl.scrollHeight;
  const previousTop = messagesEl.scrollTop;
  try {
    const data = await apiFetch(`/api/chat/rooms/${currentRoom.chat_room_id}/messages?limit=50&before_message_id=${nextBeforeMessageId}`);
    (data.messages || []).slice().reverse().forEach((message) => appendMessage(message, true));
    nextBeforeMessageId = data.next_before_message_id;
    olderMessagesButton.hidden = !data.has_more;
    messagesEl.scrollTop = previousTop + (messagesEl.scrollHeight - previousHeight);
  } catch (e) {
    showToast(e.message);
  } finally {
    olderMessagesButton.disabled = false;
  }
};
function isNearBottom() { return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight <= 120; }
function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
leaveRoomButton.onclick = async () => {
  if (!currentRoom || leaveRoomButton.hidden) return;
  if (!confirm("이 모임에서 나가시겠습니까?\n모임에서 나가면 해당 모임 채팅방에서도 나가게 됩니다.")) return;
  try {
    const room = currentRoom;
    const result = await apiFetch(`/api/meetings/${room.meeting_id}/participants/me`, { method: "DELETE" });
    currentRoom = null;
    roomTitle.textContent = "채팅방을 선택하세요";
    roomTitle.removeAttribute("href");
    roomTitle.classList.remove("is-link");
    roomStatus.hidden = true;
    leaveRoomButton.hidden = true;
    memberList.innerHTML = "";
    messagesEl.innerHTML = '<div class="empty">채팅방을 선택하세요.</div>';
    socket.emit("leave_room", { chat_room_id: room.chat_room_id });
    showToast(result.message || "모임에서 나갔습니다.");
    await loadRooms();
  } catch (e) {
    showToast(e.message);
  }
};
meetingRoomMore.onclick = () => {
  roomExpanded.meeting = !roomExpanded.meeting;
  renderRoomGroup(meetingRoomList, sortedMeetingRooms(loadedRooms.filter((r) => r.room_type !== "DIRECT")), meetingRoomMore, "meeting");
  bindRoomButtons();
};
directRoomMore.onclick = () => {
  roomExpanded.direct = !roomExpanded.direct;
  renderRoomGroup(directRoomList, loadedRooms.filter((r) => r.room_type === "DIRECT"), directRoomMore, "direct");
  bindRoomButtons();
};
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!currentRoom) return showToast("채팅방을 선택해주세요.");
  const content = e.currentTarget.content.value.trim();
  if (!content) return;
  socket.emit("send_message", { chat_room_id: currentRoom.chat_room_id, content });
  e.currentTarget.reset();
});
startChat();
