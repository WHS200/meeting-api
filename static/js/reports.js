const reportForm = document.getElementById('reportForm');
const reportQuery = new URLSearchParams(location.search);
const reportType = reportQuery.get('type');
const reportId = queryInt('id');
const reportTarget = document.getElementById('reportTarget');
const REPORT_LABELS={OPEN:'접수',IN_REVIEW:'검토 중',RESOLVED:'처리 완료',DISMISSED:'기각',USER:'사용자',MEETING:'모임',POST:'게시글'};
const reportLabel=value=>REPORT_LABELS[value]||value||'-';
if (['USER','MEETING','POST'].includes(reportType) && reportId) {
  reportForm.target_type.value = reportType;
  reportForm.target_id.value = reportId;
  reportTarget.textContent = `신고 대상: ${reportType === 'USER' ? '사용자' : reportType === 'MEETING' ? '모임' : '게시글'} #${reportId}`;
} else {
  reportTarget.textContent = '모임 또는 사용자 프로필에서 신고 버튼을 눌러 신고를 시작하세요.';
  reportForm.querySelector('button[type="submit"], button').disabled = true;
}
let reportOffset = 0;
async function loadReports(more = false) {
  if (!more) reportOffset=0;
  const data = await apiFetch('/api/reports/mine?offset='+reportOffset);
  const html = emptyList(data.reports, r=>`<article class="feature-item"><strong>#${r.report_id} · ${escapeHtml(reportLabel(r.target_type))} #${r.target_id}</strong><p>${escapeHtml(r.reason)}</p><span class="badge">${escapeHtml(reportLabel(r.status))}</span></article>`);
  const list = document.getElementById('reportList'); if(more)list.insertAdjacentHTML('beforeend',html);else list.innerHTML=html;
  reportOffset += data.reports.length; document.getElementById('moreReports').hidden=data.reports.length<30;
}
reportForm.onsubmit=e=>{e.preventDefault();featureAction(async()=>{
  const b=reportForm.querySelector('button');b.disabled=true;
  try {await apiFetch('/api/reports',jsonOptions('POST',{target_type:reportForm.target_type.value,target_id:Number(reportForm.target_id.value),reason:reportForm.reason.value,detail:reportForm.detail.value}));showToast('신고를 접수했습니다.');await loadReports();}finally{b.disabled=false;}
});};
document.getElementById('moreReports').onclick=()=>featureAction(()=>loadReports(true));
featureAction(async()=>{if(await requireLogin())await loadReports();});
