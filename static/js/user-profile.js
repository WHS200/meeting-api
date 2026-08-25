const params = new URLSearchParams(location.search);
const userId = Number(params.get("id"));
const content = document.getElementById("publicProfileContent");

async function loadPublicProfile() {
    if (!Number.isInteger(userId) || userId < 1) {
        content.innerHTML = '<div class="empty">올바른 user_id가 필요합니다.</div>';
        return;
    }

    try {
        const user = await apiFetch(`/api/users/${userId}`);
        render(user);
    } catch (error) {
        if (error.status === 401) {
            location.href = "/static/login.html";
            return;
        }
        content.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

function render(user) {
    const sports = user.sports || [];
    const sportHtml = sports.length
        ? sports.map(sport => `
            <div class="sport-item">
                <div>
                    <strong>${escapeHtml(sport.sport_name)}</strong>
                    <small>sport_id: ${sport.sport_id}</small>
                </div>
                <span class="badge">${escapeHtml(sport.skill_level)}</span>
            </div>
        `).join("")
        : '<div class="empty">등록된 운동 종목이 없습니다.</div>';

    const avatarHtml = user.profile_image
        ? `<img src="${escapeHtml(user.profile_image)}" alt="프로필 이미지">`
        : escapeHtml((user.nickname || "?").slice(0, 1));

    content.innerHTML = `
        <div class="public-head">
            <div class="avatar">${avatarHtml}</div>
            <h1>${escapeHtml(user.nickname)}</h1>
            <p class="muted">${escapeHtml(user.region || "-")}</p>
        </div>
        <div class="public-sports">
            <h2>운동 프로필</h2>
            <div class="sport-list">${sportHtml}</div>
        </div>
    `;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

loadPublicProfile();
