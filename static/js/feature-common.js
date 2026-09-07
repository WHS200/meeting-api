async function featureAction(task) {
  try { await task(); }
  catch (error) { setStatus(document.getElementById('featureStatus'), error.message, 'error'); showToast(error.message); }
}
function jsonOptions(method, body) { return {method, ...(body === undefined ? {} : {body:JSON.stringify(body)})}; }
function emptyList(rows, render) { return rows.length ? rows.map(render).join('') : '<p class="muted empty">아직 내역이 없습니다.</p>'; }
function userLabel(user) { return `<a href="/static/user-profile.html?id=${Number(user.user_id)}">${escapeHtml(user.nickname)}</a>`; }
