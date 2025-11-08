// ارسال فرم ورود
document.getElementById("loginForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  const response = await fetch("http://127.0.0.1:8000/token/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });

  const data = await response.json();

  if (response.ok) {
    // ✅ ذخیره توکن در localStorage
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);

    alert("با موفقیت وارد شدید!");
    // بستن پاپ‌آپ (اگر خواستی)
    document.getElementById("loginPopup").style.display = "none";
    updateHeaderLoginState();  // نمایش وضعیت ورود در هدر
  } else {
    alert("خطا در ورود!");
  }
});

// تابع بررسی وضعیت ورود در هدر
function updateHeaderLoginState() {
  const token = localStorage.getItem("access");
  if (token) {
    // تغییر ظاهر هدر اگر کاربر وارد است
    document.getElementById("loginPopup").style.display = "none";
    // می‌تونی اسم کاربر یا دکمه خروج اضافه کنی
  } else {
    document.getElementById("loginPopup").style.display = "block";
  }
}

// هنگام لود صفحه، وضعیت ورود رو چک کن
window.addEventListener("load", updateHeaderLoginState);
