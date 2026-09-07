let favoriteOffset=0;
async function loadFavorites(more=false){
  if(!more)favoriteOffset=0;
  const data=await apiFetch('/api/favorites?offset='+favoriteOffset);
  const html=emptyList(data.favorites,m=>`<article class="feature-item"><span class="badge">${escapeHtml(m.sport_name)}</span><h2><a href="/static/detail.html?id=${m.meeting_id}">${escapeHtml(m.title)}</a></h2><p>${escapeHtml(m.meeting_date)} ${escapeHtml(m.meeting_time)} · ${escapeHtml(m.location)}</p><div class="feature-row"><span class="badge">${escapeHtml(meetingStatusLabel(m.status))}</span><button class="btn sm" data-remove-favorite="${m.meeting_id}">관심 해제</button></div></article>`);
  const list=document.getElementById('favoriteList');if(more)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
  favoriteOffset+=data.favorites.length;document.getElementById('moreFavorites').hidden=data.favorites.length<30;
}
document.getElementById('favoriteList').onclick=e=>{const b=e.target.closest('[data-remove-favorite]');if(b)featureAction(async()=>{await apiFetch('/api/favorites/'+b.dataset.removeFavorite,jsonOptions('DELETE'));await loadFavorites();});};
document.getElementById('moreFavorites').onclick=()=>featureAction(()=>loadFavorites(true));
featureAction(async()=>{if(await requireLogin())await loadFavorites();});
