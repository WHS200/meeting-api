const sportsAdmin=location.pathname.includes('/admin/');
let proposalOffset=0,sportsOffset=0;
const SPORT_STATUS_LABELS={PENDING_REVIEW:'검토 대기',APPROVED:'승인',REJECTED:'거절',MERGED:'병합됨',ACTIVE:'활성',INACTIVE:'비활성'};
const sportStatusLabel=value=>SPORT_STATUS_LABELS[value]||value||'-';
async function loadProposals(more=false){
  if(!more)proposalOffset=0;
  const status=sportsAdmin?document.getElementById('sportReviewFilter').status.value:'';
  const url=sportsAdmin?'/api/admin/sports/proposals':'/api/sports/proposals/mine';
  const data=await apiFetch(url+'?'+new URLSearchParams({status,offset:proposalOffset}));
  const html=emptyList(data.proposals,p=>`<article class="feature-item"><div class="feature-row"><strong class="grow">#${p.proposal_id} ${escapeHtml(p.sport_name)}</strong><span class="badge">${escapeHtml(sportStatusLabel(p.status))}</span>${sportsAdmin&&p.status==='PENDING_REVIEW'?`<button class="btn" data-review="${p.proposal_id}">검토</button>`:''}</div><p>${escapeHtml(p.review_note||'검토 대기 중')}</p></article>`);
  const list=document.getElementById('proposalList');if(more)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
  proposalOffset+=data.proposals.length;document.getElementById('moreProposals').hidden=data.proposals.length<30;
}
async function loadSportsAdmin(more=false){
  if(!more)sportsOffset=0;
  const data=await apiFetch('/api/admin/sports?offset='+sportsOffset);
  const html=emptyList(data.sports,s=>`<div class="feature-item feature-row"><strong class="grow">#${s.sport_id} ${escapeHtml(s.sport_name)}</strong><span class="badge">${escapeHtml(sportStatusLabel(s.status))}</span>${s.status==='ACTIVE'?`<button class="btn" data-merge-sport="${s.sport_id}">다른 종목과 병합</button>`:''}</div>`);
  const list=document.getElementById('sportList');if(more)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
  sportsOffset+=data.sports.length;document.getElementById('moreSports').hidden=data.sports.length<30;
}
async function reviewSport(id,existing=false){
  const sports=await apiFetch('/api/sports');
  const panel=document.getElementById('sportReviewPanel');panel.hidden=false;
  panel.innerHTML=`<h2>${existing?'등록 종목 병합':'종목 신청 검토'} #${id}</h2><form id="sportReviewForm">${existing?'':`<label>처리<select name="action"><option value="approve">승인</option><option value="reject">거절</option><option value="merge">기존 종목에 병합</option></select></label>`}<label>병합 대상 (병합 시 선택)<select name="target_sport_id"><option value="">선택하세요</option>${sports.filter(s=>!existing||s.sport_id!==id).map(s=>`<option value="${s.sport_id}">${escapeHtml(s.sport_name)}</option>`).join('')}</select></label><label>처리 사유<textarea name="reason" required maxlength="1000"></textarea></label><button class="btn blue">저장</button></form>`;
  document.getElementById('sportReviewForm').onsubmit=e=>{e.preventDefault();featureAction(async()=>{
    const f=e.target,action=existing?'merge':f.action.value;
    if(action==='merge'&&!f.target_sport_id.value){showToast('병합 대상을 선택하세요.');return;}
    const url=existing?`/api/admin/sports/${id}/merge`:`/api/admin/sports/proposals/${id}/${action}`;
    await apiFetch(url,jsonOptions('POST',{reason:f.reason.value,target_sport_id:Number(f.target_sport_id.value)}));panel.hidden=true;showToast('처리했습니다.');await loadProposals();await loadSportsAdmin();
  });};
  panel.scrollIntoView({behavior:'smooth'});
}
document.getElementById('moreProposals').onclick=()=>featureAction(()=>loadProposals(true));
if(sportsAdmin){
  document.getElementById('sportReviewFilter').onsubmit=e=>{e.preventDefault();featureAction(()=>loadProposals());};
  document.getElementById('proposalList').onclick=e=>{const b=e.target.closest('[data-review]');if(b)featureAction(()=>reviewSport(Number(b.dataset.review)));};
  document.getElementById('sportList').onclick=e=>{const b=e.target.closest('[data-merge-sport]');if(b)featureAction(()=>reviewSport(Number(b.dataset.mergeSport),true));};
  document.getElementById('moreSports').onclick=()=>featureAction(()=>loadSportsAdmin(true));
}else{
  document.getElementById('sportProposalForm').onsubmit=e=>{e.preventDefault();featureAction(async()=>{await apiFetch('/api/sports/proposals',jsonOptions('POST',{sport_name:e.target.sport_name.value}));e.target.reset();showToast('종목을 신청했습니다.');await loadProposals();});};
}
featureAction(async()=>{const user=await requireLogin();if(!user)return;if(sportsAdmin&&user.role!=='ADMIN'){document.querySelector('main').innerHTML='<h1>관리자 권한이 필요합니다.</h1>';return;}await loadProposals();if(sportsAdmin)await loadSportsAdmin();});
