let socket = null,
  currentRoom = null,
  me = null;
const roomList = document.getElementById("roomList"),
  messagesEl = document.getElementById("messages"),
  roomTitle = document.getElementById("roomTitle"),
  memberList = document.getElementById("memberList"),
  messageForm = document.getElementById("messageForm");
async function startChat() {
  me = await requireLogin();
  if (!me) return;
  if (typeof io !== "function") {
    showToast("채팅 기능을 불러오지 못했습니다.");
    return;
  }
  socket = io();
  socket.on("connect_error", (e) => showToast(e.message));
  socket.on("error", (d) => showToast(d?.message || "채팅 오류"));
  socket.on("receive_message", (m) => {
    if (
      currentRoom &&
      Number(m.chat_room_id) === Number(currentRoom.chat_room_id)
    ) {
      appendMessage(m);
      scrollBottom();
    }
  });
  await loadRooms();
}
async function loadRooms() {
  try {
    const d = await apiFetch("/api/chat/rooms");
    const rooms = d.chat_rooms || [];
    roomList.innerHTML = rooms.length
      ? rooms
          .map(
            (r) =>
              `<button class="chat-room" data-room="${r.chat_room_id}"><div class="avatar">${escapeHtml((r.meeting_title || "채").slice(0, 1))}</div><div class="grow"><strong>${escapeHtml(r.meeting_title || "모임 채팅방")}</strong></div></button>`,
          )
          .join("")
      : '<div class="empty">참여 중인 채팅방이 없습니다.</div>';
    roomList.querySelectorAll("[data-room]").forEach((b, i) => {
      b.onclick = () =>
        openRoom(rooms.find((r) => r.chat_room_id === Number(b.dataset.room)));
      if (i === 0) openRoom(rooms[0]);
    });
  } catch (e) {
    roomList.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
async function openRoom(room) {
  if (!room) return;
  if (currentRoom)
    socket.emit("leave_room", { chat_room_id: currentRoom.chat_room_id });
  currentRoom = room;
  document
    .querySelectorAll(".chat-room")
    .forEach((b) =>
      b.classList.toggle(
        "active",
        Number(b.dataset.room) === room.chat_room_id,
      ),
    );
  roomTitle.textContent = room.meeting_title || "모임 채팅방";
  messagesEl.innerHTML = '<div class="empty">메시지를 불러오는 중...</div>';
  socket.emit("join_room", { chat_room_id: room.chat_room_id });
  try {
    const [m, mem] = await Promise.all([
      apiFetch(`/api/chat/rooms/${room.chat_room_id}/messages`),
      apiFetch(`/api/chat/rooms/${room.chat_room_id}/members`),
    ]);
    messagesEl.innerHTML = "";
    (m.messages || []).forEach(appendMessage);
    renderMembers(mem.members || []);
    scrollBottom();
  } catch (e) {
    messagesEl.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}
function renderMembers(members) {
  memberList.innerHTML = members
    .map((m) => `<span class="member-pill">${escapeHtml(m.nickname)}</span>`)
    .join("");
}
function appendMessage(m) {
  const mine = m.sender_nickname === me.nickname;
  const senderName = m.sender_nickname || `user ${m.sender_id}`;
  const senderId = Number(m.sender_id);
  const hasProfile = Number.isInteger(senderId) && senderId > 0;
  const avatarContent = m.sender_profile_image
    ? `<img src="${escapeHtml(m.sender_profile_image)}" alt="${escapeHtml(senderName)} 프로필">`
    : escapeHtml(senderName.slice(0, 1));
  const avatar = mine
    ? ""
    : hasProfile
      ? `<a class="avatar chat-profile-avatar" href="user-profile.html?id=${senderId}" aria-label="${escapeHtml(senderName)} 프로필 보기" title="프로필 보기">${avatarContent}</a>`
      : `<span class="avatar chat-profile-avatar">${avatarContent}</span>`;
  const div = document.createElement("div");
  div.className = `message ${mine ? "mine" : ""}`;
  div.innerHTML = `${avatar}<div class="bubble"><strong>${escapeHtml(senderName)}</strong><div>${escapeHtml(m.content)}</div><div class="message-meta">${escapeHtml(String(m.created_at || "").replace("T", " "))}</div></div>`;
  messagesEl.appendChild(div);
}
function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!currentRoom) return showToast("채팅방을 선택하세요.");
  const content = e.currentTarget.content.value.trim();
  if (!content) return;
  socket.emit("send_message", {
    chat_room_id: currentRoom.chat_room_id,
    content,
  });
  e.currentTarget.reset();
});
startChat();
