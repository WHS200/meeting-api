async function loadFriends() {
  const [friends, received, sent, blocks] = await Promise.all([
    apiFetch('/api/friends'), apiFetch('/api/friends/requests?direction=received'),
    apiFetch('/api/friends/requests?direction=sent'), apiFetch('/api/blocks')]);
  document.getElementById('friendList').innerHTML = emptyList(friends.friends, u => `<div class="feature-row feature-item"><span class="grow">${userLabel(u)}</span><button class="btn sm" data-direct="${u.user_id}">개인톡</button><button class="btn sm" data-remove="${u.user_id}">친구 삭제</button><button class="btn sm danger" data-block="${u.user_id}">차단</button></div>`);
  document.getElementById('receivedList').innerHTML = emptyList(received.requests, r => `<div class="feature-row feature-item"><span class="grow">${userLabel(r)}</span><button class="btn sm blue" data-request="${r.request_id}" data-action="accept">수락</button><button class="btn sm" data-request="${r.request_id}" data-action="reject">거절</button></div>`);
  document.getElementById('sentList').innerHTML = emptyList(sent.requests, r => `<div class="feature-row feature-item"><span class="grow">${userLabel(r)}</span><button class="btn sm" data-request="${r.request_id}" data-action="cancel">요청 취소</button></div>`);
  document.getElementById('blockList').innerHTML = emptyList(blocks.blocks, u => `<div class="feature-row feature-item"><span class="grow">${userLabel(u)}</span><button class="btn sm" data-unblock="${u.user_id}">차단 해제</button></div>`);
}
document.getElementById('searchForm').onsubmit = event => {
  event.preventDefault();
  featureAction(async () => {
    const data = await apiFetch('/api/friends/search?nickname=' + encodeURIComponent(event.target.nickname.value));
    document.getElementById('searchResults').innerHTML = emptyList(data.users, u => `<div class="feature-row feature-item"><span class="grow">${userLabel(u)}</span><button class="btn sm blue" data-add="${u.user_id}">친구 요청</button><button class="btn sm" data-direct="${u.user_id}">개인톡</button><button class="btn sm danger" data-block="${u.user_id}">차단</button></div>`);
  });
};
document.querySelector('main').onclick = event => {
  const button = event.target.closest('button');
  if (!button || button.type === 'submit' && button.closest('form')) return;
  featureAction(async () => {
    button.disabled = true;
    try {
      const d = button.dataset;
      if (d.add) await apiFetch('/api/friends/requests', jsonOptions('POST', {user_id:Number(d.add)}));
      else if (d.request) await apiFetch(`/api/friends/requests/${d.request}/${d.action}`, jsonOptions('POST'));
      else if (d.block) { if (!confirm('차단하면 친구 관계와 친구 요청이 해제됩니다. 차단할까요?')) return; await apiFetch('/api/blocks/'+d.block, jsonOptions('POST')); }
      else if (d.unblock) await apiFetch('/api/blocks/'+d.unblock, jsonOptions('DELETE'));
      else if (d.remove) await apiFetch('/api/friends/'+d.remove, jsonOptions('DELETE'));
      else if (d.direct) { const room = await apiFetch('/api/chat/direct', jsonOptions('POST', {user_id:Number(d.direct)})); location.href='/static/chat.html?room='+room.chat_room_id; return; }
      await loadFriends(); showToast('처리했습니다.');
    } finally { button.disabled = false; }
  });
};
featureAction(async () => { if (await requireLogin()) await loadFriends(); });
