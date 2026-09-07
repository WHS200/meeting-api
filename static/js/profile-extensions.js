(async()=>{
  try {
    const me=await getCurrentUser();if(!me)return;
    const id=location.pathname.endsWith('/user-profile.html')?queryInt('id'):me.user_id;
    if(!id)return;
    const stats=await apiFetch('/api/users/'+id+'/stats');
    const section=document.createElement('section');section.className='panel feature-panel activity-stats';
    section.innerHTML=`<h2>활동 통계</h2><div class="info-grid">${[['참여 모임',stats.participation_count],['출석',stats.attended_count],['노쇼',stats.no_show_count],['출석률',stats.attendance_rate===null?'기록 없음':stats.attendance_rate+'%'],['만든 모임',stats.hosted_count],['친구',stats.friend_count]].map(([label,value])=>`<div class="info-item"><small>${label}</small><strong>${escapeHtml(value)}</strong></div>`).join('')}</div><p class="muted">출석률은 출석·노쇼 처리가 완료된 기록만 계산합니다.</p>`;
    if(id!==me.user_id){
      section.insertAdjacentHTML('beforeend',`<div class="feature-row"><button class="btn" data-profile-friend>친구 요청</button><button class="btn blue" data-profile-direct>개인톡</button><button class="btn danger" data-profile-block>차단</button><a class="btn" href="/static/reports.html?type=USER&id=${id}">신고</a></div>`);
      section.onclick=async e=>{
        const b=e.target.closest('button');if(!b)return;b.disabled=true;
        try{
          if(b.hasAttribute('data-profile-friend'))await apiFetch('/api/friends/requests',{method:'POST',body:JSON.stringify({user_id:id})});
          if(b.hasAttribute('data-profile-direct')){const r=await apiFetch('/api/chat/direct',{method:'POST',body:JSON.stringify({user_id:id})});location.href='/static/chat.html?room='+r.chat_room_id;return;}
          if(b.hasAttribute('data-profile-block')){if(!confirm('친구 관계와 요청도 해제됩니다. 차단할까요?'))return;await apiFetch('/api/blocks/'+id,{method:'POST'});}
          showToast('처리했습니다.');
        }catch(error){showToast(error.message);}finally{b.disabled=false;}
      };
    }
    document.querySelector('main').append(section);
  }catch(error){showToast(error.message);}
})();
