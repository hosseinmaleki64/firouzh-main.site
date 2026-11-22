(function () {
  var API = "https://api.firouzehco.com/api/";

  function setBadge(n) {
    document.querySelectorAll(".cart-badge").forEach(function (el) {
      el.textContent = n;
      el.style.display = n > 0 ? "" : "none";
    });
  }

  async function refreshToken() {
    var refresh = localStorage.getItem("refresh");
    if (!refresh) return false;
    try {
      var res = await fetch(API + "auth/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refresh })
      });
      if (!res.ok) return false;
      var d = await res.json();
      if (!d.access) return false;
      localStorage.setItem("access", d.access);
      return true;
    } catch (e) { return false; }
  }

  async function loadCart(useToken, retried) {
    var headers = {};
    var token = localStorage.getItem("access");
    if (useToken && token) headers["Authorization"] = "Bearer " + token;
    var res = await fetch(API + "cart/", { headers: headers, credentials: "include" });
    if (res.status === 401 && useToken) {
      if (!retried && await refreshToken()) return loadCart(true, true);
      return loadCart(false, true);
    }
    if (!res.ok) throw new Error("cart " + res.status);
    return res.json();
  }

  function init() {
    loadCart(true, false)
      .then(function (cart) { setBadge(Number(cart.total_items) || 0); })
      .catch(function () { setBadge(0); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
