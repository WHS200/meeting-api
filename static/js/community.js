let postOffset = 0;
const BOARD_LABELS={FREE:'자유게시판',TIPS:'운동 팁',NOTICE:'공지사항'};
const boardLabel=value=>BOARD_LABELS[value]||'전체 게시판';
async function loadPosts(append = false) {
  const form = document.getElementById('postSearch');
  if (!append) postOffset = 0;
  const query = new URLSearchParams({board:form.board.value, keyword:form.keyword.value, offset:postOffset});
  const data = await apiFetch('/api/community/posts?'+query);
  const html = emptyList(data.posts, p => `<article class="feature-item"><span class="badge">${escapeHtml(boardLabel(p.board))}</span><h2><a href="/static/post-detail.html?id=${p.post_id}">${escapeHtml(p.title)}</a></h2><p class="muted">${escapeHtml(p.author_nickname)} · ${escapeHtml(p.created_at)}</p></article>`);
  const list = document.getElementById('postList');
  if (append) list.insertAdjacentHTML('beforeend', html); else list.innerHTML = html;
  postOffset += data.posts.length;
  document.getElementById('loadMore').hidden = data.posts.length < 30;
}
document.getElementById('postSearch').onsubmit = e => {e.preventDefault(); featureAction(() => loadPosts());};
document.getElementById('loadMore').onclick = () => featureAction(() => loadPosts(true));
document.querySelectorAll('[data-board]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-board]').forEach(item => item.classList.toggle('active', item === button));
  document.querySelector('#postSearch [name="board"]').value = button.dataset.board;
  featureAction(() => loadPosts());
}));
featureAction(async () => { if (await requireLogin()) await loadPosts(); });
