(function(){
  var API="https://api.firouzehco.com",CART=API+"/api/cart";
  function tok(){try{return localStorage.getItem("access")}catch(e){return null}}
  async function refreshTok(){
    var r;try{r=localStorage.getItem("refresh")}catch(e){}
    if(!r)return false;
    try{
      var res=await fetch(API+"/api/auth/refresh/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh:r})});
      if(!res.ok)return false;
      var d=await res.json();if(!d.access)return false;
      localStorage.setItem("access",d.access);return true;
    }catch(e){return false}
  }
  async function cartFetch(path,opts,retry){
    opts=opts||{};
    var h=Object.assign({},opts.headers||{});
    if(opts.body)h["Content-Type"]="application/json";
    var t=tok();if(t)h["Authorization"]="Bearer "+t;
    var res=await fetch(CART+path,Object.assign({},opts,{headers:h,credentials:"include"}));
    if(res.status===401&&!retry){
      if(await refreshTok())return cartFetch(path,opts,true);
      try{localStorage.removeItem("access");localStorage.removeItem("refresh")}catch(e){}
      return cartFetch(path,opts,true);
    }
    if(!res.ok){var err=await res.json().catch(function(){return{}});throw err}
    return res.json();
  }
  function toast(msg){
    var t=document.getElementById("toast");if(!t)return;
    t.innerHTML=msg;t.style.display="block";
    clearTimeout(toast._t);toast._t=setTimeout(function(){t.style.display="none"},3500);
  }
  function badge(){
    var b=document.getElementById("cartBadge");if(!b)return;
    cartFetch("/").then(function(c){b.textContent=c.total_items||0}).catch(function(){});
  }
  badge();
  var q=document.getElementById("qtyInput");
  var dec=document.getElementById("qtyDec"),inc=document.getElementById("qtyInc");
  if(q&&dec&&inc){
    dec.addEventListener("click",function(){q.value=Math.max(1,Number(q.value)-1)});
    inc.addEventListener("click",function(){q.value=Number(q.value)+1});
  }
  var add=document.getElementById("addBtn");
  if(add){
    add.addEventListener("click",async function(){
      add.disabled=true;var old=add.innerHTML;add.textContent="در حال افزودن...";
      try{
        await cartFetch("/items/",{method:"POST",body:JSON.stringify({product_id:add.dataset.id,quantity:Number(q?q.value:1)||1})});
        badge();
        toast('به سبد خرید اضافه شد. <a href="/checkout.html" style="color:#7ee0d6">ثبت سفارش</a>');
      }catch(e){toast((e&&e.detail)||"خطا در افزودن به سبد خرید")}
      add.disabled=false;add.innerHTML=old;
    });
  }
  var main=document.getElementById("mainImg");
  document.querySelectorAll(".thumbs img").forEach(function(im){
    im.addEventListener("click",function(){
      if(main){main.src=im.dataset.full}
      document.querySelectorAll(".thumbs img").forEach(function(x){x.classList.remove("on")});
      im.classList.add("on");
    });
  });
})();
