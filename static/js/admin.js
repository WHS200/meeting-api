const adminList = document.getElementById('adminList');
const adminKind = adminList?.dataset.kind;
let adminOffset=0;
const ADMIN_LABELS={
  ACTIVE:'활성',SUSPENDED:'정지',DELETED:'삭제됨',
  RECRUITING:'모집 중',CLOSED:'모집 마감',COMPLETED:'종료',CANCELED:'취소',
  OPEN:'접수',IN_REVIEW:'검토 중',RESOLVED:'처리 완료',DISMISSED:'기각',
  FREE:'자유',TIPS:'운동 팁',NOTICE:'공지',USER:'사용자',MEETING:'모임',POST:'게시글',
  ADMIN:'관리자',USER_ACTION:'사용자 조치',SUSPEND:'기간 정지',UNSUSPEND:'정지 해제',SUSPEND_USER:'사용자 정지',CANCEL_MEETING:'모임 취소',DELETE_POST:'게시글 삭제',NONE:'조치 없음',
};
const adminLabel=value=>ADMIN_LABELS[value]||value||'-';
function translateAdminFilters(){
  document.querySelectorAll('#adminSearch option,#sportReviewFilter option').forEach(option=>{
    const value=option.value||option.textContent.trim();
    option.textContent=ADMIN_LABELS[value]||option.textContent;
  });
}
async function loadAdmin(more=false) {
  if(!more) adminOffset=0;
  const query = new URLSearchParams(new FormData(document.getElementById('adminSearch'))); query.set('offset',adminOffset);
  const data=await apiFetch('/api/admin/'+adminKind+'?'+query);
  const rows=data[adminKind];
  const html=emptyList(rows,row=>{
    const id=row.user_id || row.meeting_id || row.report_id || row.post_id;
    const title=row.nickname || row.title || row.reason;
    return `<article class="feature-item"><div class="feature-row"><strong class="grow">#${id} ${escapeHtml(title)}</strong><span class="badge">${escapeHtml(adminLabel(row.status || row.board))}</span><button class="btn sm" data-detail="${id}">${adminKind==='users'||adminKind==='reports'?'상세·처리':'관리'}</button></div>${row.target_type?`<p>${escapeHtml(adminLabel(row.target_type))} #${row.target_id}</p>`:''}</article>`;
  });
  if(more)adminList.insertAdjacentHTML('beforeend',html);else adminList.innerHTML=html;
  adminOffset+=rows.length;document.getElementById('adminMore').hidden=rows.length<30;
}
async function adminDetail(id) {
  const panel=document.getElementById('adminDetail');panel.hidden=false;
  if(adminKind==='users') {
    const data=await apiFetch('/api/admin/users/'+id),u=data.user;
    panel.innerHTML=`<h2>${escapeHtml(u.nickname)} · #${u.user_id}</h2><p>${escapeHtml(u.email)} · ${escapeHtml(adminLabel(u.status))} · ${escapeHtml(adminLabel(u.role))}</p><p>정지 종료: ${escapeHtml(u.suspended_until||'-')}</p><p>최근 사유: ${escapeHtml(u.suspension_reason||'-')}</p><form id="userModeration"><label>정지 기간 (1~365일)<input name="days" type="number" min="1" max="365" value="7" required></label><label>처리 사유<textarea name="reason" maxlength="1000" required></textarea></label><button class="btn danger" name="action" value="suspend">기간 정지</button> <button class="btn" name="action" value="unsuspend">정지 해제</button></form><h3>처리 이력</h3>${emptyList(data.actions,a=>`<p>${escapeHtml(adminLabel(a.action))} · ${escapeHtml(a.reason)} · ${escapeHtml(a.created_at)}</p>`)}`;
    document.getElementById('userModeration').onsubmit=e=>{e.preventDefault();const action=e.submitter.value;featureAction(async()=>{
      await apiFetch(`/api/admin/users/${id}/${action}`,jsonOptions('POST',{days:Number(e.target.days.value),reason:e.target.reason.value}));showToast('처리했습니다.');await loadAdmin();await adminDetail(id);
    });};
  } else if(adminKind==='reports') {
    const r=(await apiFetch('/api/admin/reports/'+id)).report;
    const path={USER:'user-profile',MEETING:'detail',POST:'post-detail'}[r.target_type];
    const action={USER:'SUSPEND_USER',MEETING:'CANCEL_MEETING',POST:'DELETE_POST'}[r.target_type];
    const suspensionField = r.target_type === 'USER' ? '<label>사용자 정지 기간 (일)<input name="days" type="number" min="1" max="365" value="7"></label>' : '';
    panel.innerHTML=`<h2>신고 #${id}</h2><a class="btn" href="/static/${path}.html?id=${r.target_id}">신고 대상 ${escapeHtml(adminLabel(r.target_type))} #${r.target_id} 확인</a><p>신고자 ID: ${r.reporter_id} (관리자 전용)</p><strong>${escapeHtml(r.reason)}</strong><p class="feature-copy">${escapeHtml(r.detail)}</p><p>처리자: ${escapeHtml(r.processed_by||'-')} · ${escapeHtml(r.processed_at||'-')}</p><p class="feature-copy">${escapeHtml(r.process_note||'')}</p><form id="reportModeration"><label>처리 상태<select name="status"><option value="IN_REVIEW" ${r.status==='IN_REVIEW'?'selected':''}>검토 중</option><option value="RESOLVED" ${r.status==='RESOLVED'?'selected':''}>처리 완료</option><option value="DISMISSED" ${r.status==='DISMISSED'?'selected':''}>기각</option></select></label><label>함께 실행할 조치<select name="action"><option value="NONE">조치 없음</option><option value="${action}">${escapeHtml(adminLabel(action))}</option></select></label>${suspensionField}<label>관리자 메모<textarea name="process_note" maxlength="1000" required></textarea></label><button class="btn blue" ${['RESOLVED','DISMISSED'].includes(r.status)?'disabled':''}>처리 저장</button></form>`;
    document.getElementById('reportModeration').onsubmit=e=>{e.preventDefault();featureAction(async()=>{
      const f=e.target;const payload={status:f.status.value,action:f.action.value,process_note:f.process_note.value};if(f.days)payload.days=Number(f.days.value);await apiFetch('/api/admin/reports/'+id,jsonOptions('PATCH',payload));showToast('처리했습니다.');await loadAdmin();await adminDetail(id);
    });};
  } else {
    const isPost=adminKind==='posts';
    panel.innerHTML=`<h2>${isPost?'게시글 삭제':'모임 취소'} #${id}</h2><a class="btn" href="/static/${isPost?'post-detail':'detail'}.html?id=${id}">내용 확인</a><form id="contentModeration"><label>관리 사유<textarea name="reason" required maxlength="1000"></textarea></label><button class="btn danger">${isPost?'삭제':'취소'} 실행</button></form>`;
    document.getElementById('contentModeration').onsubmit=e=>{e.preventDefault();featureAction(async()=>{
      if(!confirm('관리 조치를 실행할까요?'))return;
      await apiFetch(`/api/admin/${adminKind}/${id}${isPost?'':'/cancel'}`,jsonOptions(isPost?'DELETE':'POST',{reason:e.target.reason.value}));panel.hidden=true;showToast('처리했습니다.');await loadAdmin();
    });};
  }
  panel.scrollIntoView({behavior:'smooth',block:'start'});
}
if(adminList) {
  adminList.onclick=e=>{const b=e.target.closest('[data-detail]');if(b)featureAction(()=>adminDetail(Number(b.dataset.detail)));};
  document.getElementById('adminSearch').onsubmit=e=>{e.preventDefault();featureAction(()=>loadAdmin());};
  document.getElementById('adminMore').onclick=()=>featureAction(()=>loadAdmin(true));
}
document.getElementById('noticeForm')?.addEventListener('submit',e=>{e.preventDefault();featureAction(async()=>{
  await apiFetch('/api/admin/notices',jsonOptions('POST',{title:e.target.title.value,content:e.target.content.value}));e.target.reset();showToast('공지를 등록했습니다.');await loadAdmin();
});});
featureAction(async()=>{
  const u=await requireLogin();if(!u)return;
  if(u.role!=='ADMIN'){document.querySelector('main').innerHTML='<h1>관리자 권한이 필요합니다.</h1><a href="/static/index.html">모임으로 돌아가기</a>';return;}
  translateAdminFilters();
  if(adminList)await loadAdmin();else document.getElementById('adminHome').hidden=false;
});
