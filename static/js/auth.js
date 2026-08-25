const page = document.body.dataset.page;
if (page === "login") {
  const form = document.getElementById("loginForm"),
    status = document.getElementById("formStatus");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(status, "로그인 중...");
    try {
      await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          login_id: form.login_id.value,
          password: form.password.value,
        }),
      });
      setStatus(status, "로그인 성공", "success");
      setTimeout(redirectAfterLogin, 250);
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });
}
if (page === "signup") {
  const form = document.getElementById("signupForm"),
    status = document.getElementById("formStatus");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.password.value !== form.password_confirm.value) {
      setStatus(status, "비밀번호 확인이 일치하지 않습니다.", "error");
      return;
    }
    const body = {
      login_id: form.login_id.value,
      password: form.password.value,
      nickname: form.nickname.value,
      email: form.email.value,
      birth_date: form.birth_date.value,
      gender: form.gender.value,
      region: form.region.value,
    };
    setStatus(status, "가입 중...");
    try {
      await apiFetch("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setStatus(status, "회원가입 완료", "success");
      setTimeout(() => (location.href = "/static/login.html"), 350);
    } catch (error) {
      setStatus(status, error.message, "error");
    }
  });
}
