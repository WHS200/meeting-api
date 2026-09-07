let notificationOffset=0;
function notificationLink(n) {
  if(n.target_type==='MEETING')return '/static/detail.html?id='+Number(n.target_id);
  if(n.target_type==='USER')return '/static/user-profile.html?id='+Number(n.target_id);
  if(n.target_type==='FRIEND_REQUEST')return '/static/friends.html';
  if(n.target_type==='REPORT')return '/static/reports.html';
  return '/static/notifications.html';
}
async function loadNotifications(more=false) {
  if(!more)notificationOffset=0;
  const [data,count]=await Promise.all([apiFetch('/api/notifications?offset='+notificationOffset),apiFetch('/api/notifications/unread-count')]);
  document.getElementById('unreadCount').textContent='읽지 않은 알림 '+count.count+'개';
  const html=emptyList(data.notifications,n=>`<article class="feature-item ${n.read_at?'':'unread'}"><div class="feature-row"><a class="grow" href="${notificationLink(n)}">${escapeHtml(n.message)}</a>${n.read_at?'<span class="muted">읽음</span>':`<button class="btn sm" data-read="${n.notification_id}">읽음 처리</button>`}</div><p class="muted">${escapeHtml(n.created_at)}</p></article>`);
  const list=document.getElementById('notificationList');if(more)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
  notificationOffset+=data.notifications.length;document.getElementById('moreNotifications').hidden=data.notifications.length<30;
}
document.getElementById('notificationList').onclick=e=>{const b=e.target.closest('[data-read]');if(b)featureAction(async()=>{await apiFetch('/api/notifications/'+b.dataset.read+'/read',jsonOptions('POST'));await loadNotifications();});};
document.getElementById('readAll').onclick=()=>featureAction(async()=>{await apiFetch('/api/notifications/read-all',jsonOptions('POST'));await loadNotifications();});
document.getElementById('moreNotifications').onclick=()=>featureAction(()=>loadNotifications(true));
featureAction(async()=>{if(await requireLogin())await loadNotifications();});
