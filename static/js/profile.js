const SKILL_LEVELS = ["BRONZE", "SILVER", "GOLD", "MASTER"];

let me = null;
let sports = [];
let mySports = [];

const nicknameText = document.getElementById("nicknameText");
const regionText = document.getElementById("regionText");
const loginIdText = document.getElementById("loginIdText");
const emailText = document.getElementById("emailText");
const birthText = document.getElementById("birthText");
const genderText = document.getElementById("genderText");
const avatar = document.getElementById("avatar");
const sportList = document.getElementById("sportList");
const sportSelect = document.getElementById("sportSelect");

async function loadMe() {
    try {
        me = await apiFetch("/api/users/me");
        renderMe();
    } catch (error) {
        if (error.status === 401) {
            location.href = "/static/login.html";
            return;
        }
        showToast(error.message);
    }
}

function renderMe() {
    nicknameText.textContent = me.nickname;
    regionText.textContent = me.region;
    loginIdText.textContent = me.login_id;
    emailText.textContent = me.email;
    birthText.textContent = me.birth_date || "-";
    genderText.textContent = me.gender || "-";

    avatar.innerHTML = "";
    if (me.profile_image) {
        const img = document.createElement("img");
        img.src = me.profile_image;
        img.alt = "프로필 이미지";
        avatar.appendChild(img);
    } else {
        avatar.textContent = (me.nickname || "?").slice(0, 1);
    }

    document.getElementById("nicknameInput").value = me.nickname || "";
    document.getElementById("regionInput").value = me.region || "";
}

async function loadSports() {
    try {
        sports = await apiFetch("/api/sports");
        sportSelect.innerHTML = "";

        for (const sport of sports) {
            const option = document.createElement("option");
            option.value = sport.sport_id;
            option.textContent = sport.sport_name;
            sportSelect.appendChild(option);
        }

        if (!sports.length) {
            const option = document.createElement("option");
            option.textContent = "활성 종목 없음";
            option.disabled = true;
            option.selected = true;
            sportSelect.appendChild(option);
        }
    } catch (error) {
        showToast(error.message);
    }
}

async function loadMySports() {
    try {
        const data = await apiFetch("/api/users/me/sports");
        mySports = data.sports || [];
        renderMySports();
    } catch (error) {
        if (error.status === 401) {
            location.href = "/static/login.html";
            return;
        }
        showToast(error.message);
    }
}

function renderMySports() {
    sportList.innerHTML = "";

    if (!mySports.length) {
        sportList.innerHTML = '<div class="empty">등록된 운동 종목이 없습니다.</div>';
        return;
    }

    for (const sport of mySports) {
        const item = document.createElement("div");
        item.className = "sport-item";

        const info = document.createElement("div");
        info.innerHTML = `<strong>${escapeHtml(sport.sport_name)}</strong><small>sport_id: ${sport.sport_id}</small>`;

        const actions = document.createElement("div");
        actions.className = "actions";

        const level = document.createElement("select");
        for (const value of SKILL_LEVELS) {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            option.selected = value === sport.skill_level;
            level.appendChild(option);
        }

        const updateButton = document.createElement("button");
        updateButton.className = "btn sm";
        updateButton.textContent = "실력 수정";
        updateButton.addEventListener("click", () => updateSport(sport.sport_id, level.value));

        const deleteButton = document.createElement("button");
        deleteButton.className = "btn sm danger";
        deleteButton.textContent = "삭제";
        deleteButton.addEventListener("click", () => deleteSport(sport.sport_id, sport.sport_name));

        actions.append(level, updateButton, deleteButton);
        item.append(info, actions);
        sportList.appendChild(item);
    }
}

async function updateSport(sportId, skillLevel) {
    try {
        const data = await apiFetch(`/api/users/me/sports/${sportId}`, {
            method: "PATCH",
            body: JSON.stringify({skill_level: skillLevel})
        });
        showToast(data.message);
        await loadMySports();
    } catch (error) {
        showToast(error.message);
    }
}

async function deleteSport(sportId, sportName) {
    if (!confirm(`${sportName} 종목을 삭제할까요?`)) return;

    try {
        const data = await apiFetch(`/api/users/me/sports/${sportId}`, {
            method: "DELETE"
        });
        showToast(data.message);
        await loadMySports();
    } catch (error) {
        showToast(error.message);
    }
}

document.getElementById("profileForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const body = {
        nickname: event.currentTarget.nickname.value,
        region: event.currentTarget.region.value
    };

    try {
        const data = await apiFetch("/api/users/me", {
            method: "PATCH",
            body: JSON.stringify(body)
        });
        showToast(data.message);
        await loadMe();
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("sportForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!sports.length) {
        showToast("활성 종목이 없습니다.");
        return;
    }

    const body = {
        sport_id: Number(event.currentTarget.sport_id.value),
        skill_level: event.currentTarget.skill_level.value
    };

    try {
        const data = await apiFetch("/api/users/me/sports", {
            method: "POST",
            body: JSON.stringify(body)
        });
        showToast(data.message);
        await loadMySports();
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("imageForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = event.currentTarget.profile_image.files[0];
    if (!file) {
        showToast("이미지 파일을 선택하세요.");
        return;
    }

    const formData = new FormData();
    formData.append("profile_image", file);

    try {
        const data = await apiFetch("/api/users/me/profile-image", {
            method: "POST",
            body: formData
        });
        showToast(data.message);
        await loadMe();
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("passwordForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const body = {
        current_password: event.currentTarget.current_password.value,
        new_password: event.currentTarget.new_password.value
    };

    try {
        const data = await apiFetch("/api/users/me/password", {
            method: "PATCH",
            body: JSON.stringify(body)
        });
        showToast(data.message);
        event.currentTarget.reset();
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("logoutButton").addEventListener("click", async () => {
    try {
        await apiFetch("/api/auth/logout", {method: "POST"});
        location.href = "/static/login.html";
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("deleteButton").addEventListener("click", async () => {
    const confirmed = confirm("계정을 삭제할까요? 이 작업은 현재 API의 soft delete를 실행합니다.");
    if (!confirmed) return;

    try {
        const data = await apiFetch("/api/users/me", {method: "DELETE"});
        alert(data.message);
        location.href = "/static/login.html";
    } catch (error) {
        showToast(error.message);
    }
});

document.getElementById("lookupForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const userId = Number(event.currentTarget.user_id.value);
    if (!Number.isInteger(userId) || userId < 1) {
        showToast("올바른 user_id를 입력하세요.");
        return;
    }
    location.href = `/static/user-profile.html?id=${userId}`;
});

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

Promise.all([loadMe(), loadSports(), loadMySports()]);
