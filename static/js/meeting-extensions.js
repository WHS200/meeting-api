(async()=>{
  try{
    const user=await getCurrentUser(),id=queryInt('id');if(!user||!id)return;
    const section=document.createElement('section');section.className='panel feature-panel';section.id='meetingExtensions';
    section.innerHTML=`<h2>모임 소식과 관심</h2><div class="feature-row"><button class="btn" data-favorite-add>관심 등록</button><button class="btn" data-favorite-remove>관심 해제</button><a class="btn" href="/static/reports.html?type=MEETING&id=${id}">모임 신고</a></div><div id="waitingInfo"></div>`;
    section.onclick=async e=>{const b=e.target.closest('button');if(!b)return;b.disabled=true;
      try{if(b.hasAttribute('data-favorite-add'))await apiFetch('/api/favorites/'+id,{method:'POST'});else if(b.hasAttribute('data-favorite-remove'))await apiFetch('/api/favorites/'+id,{method:'DELETE'});showToast('처리했습니다.');}catch(error){showToast(error.message);}finally{b.disabled=false;}
    };
    document.querySelector('main').append(section);
    async function refreshWaiting(){
      const result=await apiFetch(`/api/meetings/${id}/waitlist`);
      const list=document.getElementById('waitingInfo');
      list.innerHTML=`<h3>정원 대기 ${result.total}명</h3><p class="muted">즉시 승인 모임은 만석일 때 대기자로 등록됩니다. 모임장 승인 방식은 승인 후 대기열에 등록됩니다. 자리가 나면 일정이 겹치지 않는 대기자부터 승급합니다.</p>`+(result.waitlist||[]).map(w=>`<p>${w.position}번째 · ${escapeHtml(w.nickname)}</p>`).join('');
    }
    window.addEventListener('participation-changed',()=>refreshWaiting().catch(e=>showToast(e.message)));
    await refreshWaiting();
  }catch(error){showToast(error.message);}
})();
