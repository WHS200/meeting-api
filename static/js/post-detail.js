const postId = queryInt('id');
let postUser, loadedPost, commentsOffset = 0;
const postForm = document.getElementById('postForm');
const COMMUNITY_BOARD_LABELS={FREE:'자유게시판',TIPS:'운동 팁',NOTICE:'공지사항'};
async function loadPost(more = false) {
  if (!more) commentsOffset = 0;
  const data = await apiFetch(`/api/community/posts/${postId}?offset=${commentsOffset}`);
  loadedPost = data.post;
  const allowed = postUser.user_id === loadedPost.author_id || postUser.role === 'ADMIN';
  const view = document.getElementById('postView'); view.hidden = false;
  view.innerHTML = `<span class="badge">${escapeHtml(COMMUNITY_BOARD_LABELS[loadedPost.board] || loadedPost.board)}</span><h2>${escapeHtml(loadedPost.title)}</h2><p class="muted">${escapeHtml(loadedPost.author_nickname)}</p><div class="feature-copy">${escapeHtml(loadedPost.content)}</div><div class="feature-row">${allowed ? '<button class="btn" id="editPost">수정</button><button class="btn danger" id="deletePost">삭제</button>' : `<a class="btn" href="/static/reports.html?type=POST&id=${postId}">신고</a>`}</div>`;
  document.getElementById('postEditor').hidden = true;
  document.getElementById('commentsPanel').hidden = false;
  const html = emptyList(data.comments, c => `<div class="feature-item"><strong>${escapeHtml(c.author_nickname)}</strong><p class="feature-copy">${escapeHtml(c.content)}</p>${c.author_id === postUser.user_id || postUser.role === 'ADMIN' ? `<button class="btn sm" data-comment="${c.comment_id}">삭제</button>` : ''}</div>`);
  const list = document.getElementById('commentList');
  if (more) list.insertAdjacentHTML('beforeend', html); else list.innerHTML = html;
  commentsOffset += data.comments.length;
  document.getElementById('moreComments').hidden = data.comments.length < 30;
  if (allowed) {
    document.getElementById('editPost').onclick = () => {
      postForm.board.value = loadedPost.board; postForm.title.value = loadedPost.title; postForm.content.value = loadedPost.content;
      document.getElementById('editorTitle').textContent = '글 수정'; document.getElementById('postEditor').hidden = false;
    };
    document.getElementById('deletePost').onclick = () => featureAction(async () => {
      if (!confirm('게시글을 삭제할까요?')) return;
      await apiFetch('/api/community/posts/'+postId, jsonOptions('DELETE')); location.href='/static/community.html';
    });
  }
}
postForm.onsubmit = e => {e.preventDefault(); featureAction(async () => {
  const data = await apiFetch('/api/community/posts'+(postId ? '/'+postId : ''), jsonOptions(postId ? 'PUT':'POST', {board:postForm.board.value,title:postForm.title.value,content:postForm.content.value}));
  location.href='/static/post-detail.html?id='+(postId || data.post_id);
});};
document.getElementById('commentForm').onsubmit = e => {e.preventDefault(); featureAction(async () => {
  await apiFetch(`/api/community/posts/${postId}/comments`, jsonOptions('POST', {content:e.target.content.value})); e.target.reset(); await loadPost();
});};
document.getElementById('commentList').onclick = e => {const b=e.target.closest('[data-comment]'); if(b) featureAction(async () => {await apiFetch('/api/community/comments/'+b.dataset.comment,jsonOptions('DELETE'));await loadPost();});};
document.getElementById('moreComments').onclick = () => featureAction(() => loadPost(true));
featureAction(async () => {postUser = await requireLogin(); if (!postUser) return; document.getElementById('noticeOption').hidden = postUser.role !== 'ADMIN'; if(postId) await loadPost();});
