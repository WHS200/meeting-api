let socket = null, currentRoom = null, me = null;
const meetingRoomList = document.getElementById("meetingRoomList");
const directRoomList = document.getElementById("directRoomList");
const messagesEl = document.getElementById("messages");
const roomTitle = document.getElementById("roomTitle");
const memberList = document.getElementById("memberList");
const messageForm = document.getElementById("messageForm");

async function startChat() {
  me = await requireLogin();
  if (!me) return;
  if (typeof io !== "function") return showToast("채팅 기능을 불러오지 못했습니다.");
  socket = io();
  socket.on("connect_error", (e) => showToast(e.message));
  socket.on("error", (d) => showToast(d?.message || "채팅 오류"));
  socket.on("receive_message", (m) => {
    if (currentRoom && Number(m.chat_room_id) === Number(currentRoom.chat_room_id)) {
      appendMessage(m);
      scrollBottom();
    }
  });
  await loadRooms();
}

function roomButton(room) {
  const title = room.meeting_title || room.direct_nickname || (room.room_type === "DIRECT" ? `개인 채팅 #${room.chat_room_id}` : `모임 채팅방 #${room.chat_room_id}`);
  const avatar = room.direct_profile_image
    ? `<img src="${escapeHtml(room.direct_profile_image)}" alt="">`
    : escapeHtml((room.meeting_title || room.direct_nickname || "채").slice(0, 1));
  return `<button class="chat-room" data-room="${room.chat_room_id}"><div class="avatar">${avatar}</div><div class="grow"><strong>${escapeHtml(title)}</strong></div></button>`;
}

async function loadRooms() {
  try {
    const d = await apiFetch("/api/chat/rooms");
    const rooms = d.chat_rooms || [];
    const meetingRooms = rooms.filter((r) => r.room_type !== "DIRECT");
    const directRooms = rooms.filter((r) => r.room_type === "DIRECT");
    meetingRoomList.innerHTML = meetingRooms.length ? meetingRooms.map(roomButton).join("") : '<div class="empty">모임 채팅방이 없습니다.</div>';
    directRoomList.innerHTML = directRooms.length ? directRooms.map(roomButton).join("") : '<div class="empty">개인 채팅방이 없습니다.</div>';
    document.querySelectorAll("[data-room]").forEach((button) => {
      button.onclick = () => openRoom(rooms.find((r) => r.chat_room_id === Number(button.dataset.room)));
    });
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
  document.querySelectorAll("[data-room]").forEach((b) => b.classList.toggle("active", Number(b.dataset.room) === room.chat_room_id));
  roomTitle.textContent = room.meeting_title || room.direct_nickname || "개인 채팅";
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
  memberList.innerHTML = members.map((m) => `<span class="member-pill">${escapeHtml(m.nickname)}</span>`).join("");
}
function appendMessage(m) {
  const mine = m.sender_nickname === me.nickname;
  const senderName = m.sender_nickname || `사용자 ${m.sender_id}`;
  const senderId = Number(m.sender_id);
  const avatarContent = m.sender_profile_image ? `<img src="${escapeHtml(m.sender_profile_image)}" alt="${escapeHtml(senderName)} 프로필">` : escapeHtml(senderName.slice(0, 1));
  const avatar = mine ? "" : `<a class="avatar chat-profile-avatar" href="user-profile.html?id=${senderId}" aria-label="${escapeHtml(senderName)} 프로필 보기">${avatarContent}</a>`;
  const div = document.createElement("div");
  div.className = `message ${mine ? "mine" : ""}`;
  div.innerHTML = `${avatar}<div class="bubble"><strong>${escapeHtml(senderName)}</strong><div>${escapeHtml(m.content)}</div><div class="message-meta">${escapeHtml(String(m.created_at || "").replace("T", " "))}</div></div>`;
  messagesEl.appendChild(div);
}
function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!currentRoom) return showToast("채팅방을 선택해주세요.");
  const content = e.currentTarget.content.value.trim();
  if (!content) return;
  socket.emit("send_message", { chat_room_id: currentRoom.chat_room_id, content });
  e.currentTarget.reset();
});
startChat();
