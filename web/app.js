/* 宠物朋友圈 · 前端（原生 JS，无构建步骤） */

const screenEl = document.getElementById("screen");
const fab = document.getElementById("fab");
const sheet = document.getElementById("sheet");
const bussy = document.getElementById("bussy");
const bussyText = document.getElementById("bussyText");
const toastEl = document.getElementById("toast");
const eventInput = document.getElementById("eventInput");
const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const previewImg = document.getElementById("previewImg");

let state = null;
let currentFile = null;
let toastTimer = null;

const EVENT_SAMPLES = [
  "偷吃了半块蛋黄酥",
  "把新纸箱霸占了",
  "凌晨三点在走廊跑酷",
  "被吸尘器吓到躲进衣柜",
  "洗澡的时候骂了十分钟",
  "和镜子里的自己打了一架",
  "第一次见到雪",
  "在阳台看鸟看了四十分钟",
];

const TRAIT_SAMPLES = [
  "贪吃",
  "嘴硬心软",
  "半夜跑酷",
  "爱拆家",
  "超黏人",
  "高冷",
  "见人就躲",
  "窝里横",
];

/* ------------------------------------------------------------ 工具 */

const esc = (str = "") =>
  String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function speciesEmoji(species = "") {
  if (/猫|喵|cat/i.test(species)) return "🐱";
  if (/狗|汪|dog|柯基|柴|金毛|泰迪|边牧/i.test(species)) return "🐶";
  if (/兔|rabbit/i.test(species)) return "🐰";
  if (/仓鼠|hamster/i.test(species)) return "🐹";
  if (/鸟|鹦鹉|bird/i.test(species)) return "🐦";
  if (/龟|turtle/i.test(species)) return "🐢";
  if (/猪|pig/i.test(species)) return "🐷";
  return "🐾";
}

function fmtTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const dayMs = 86400000;
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startThat = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = Math.round((startToday - startThat) / dayMs);
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  if (diff <= 0) return `今天 ${hm}`;
  if (diff === 1) return `昨天 ${hm}`;
  if (diff < 7) return `${diff} 天前 ${hm}`;
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`;
}

function daysTogether(posts) {
  if (!posts.length) return 1;
  const first = new Date(posts[posts.length - 1].created_at);
  const days = Math.floor((Date.now() - first.getTime()) / 86400000) + 1;
  return Math.max(1, days);
}

function toast(msg, ms = 2400) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  toastEl.style.animation = "none";
  void toastEl.offsetWidth;
  toastEl.style.animation = "";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toastEl.hidden = true), ms);
}

function showBussy(text) {
  bussyText.textContent = text;
  bussy.hidden = false;
}

function hideBussy() {
  bussy.hidden = true;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = `请求失败（${res.status}）`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

/* ------------------------------------------------------------ 渲染：创建页 */

function renderWelcome() {
  fab.hidden = true;
  screenEl.innerHTML = `
    <div class="welcome">
      <h1>给你家那位<br />开个<em>朋友圈</em></h1>
      <p class="lead">它负责活着，AI 负责把它今天干的破事写成一条动态，<br />隔壁的猫狗会来评论区抬杠。</p>

      <div class="field">
        <label>它叫什么</label>
        <input id="nameInput" maxlength="12" placeholder="豆花" autocomplete="off" />
      </div>

      <div class="field-row">
        <div class="field">
          <label>是什么品种</label>
          <input id="speciesInput" maxlength="20" placeholder="英短蓝猫" list="speciesList" autocomplete="off" />
          <datalist id="speciesList">
            <option>英短蓝猫</option><option>橘猫</option><option>布偶猫</option>
            <option>中华田园猫</option><option>柯基</option><option>金毛</option>
            <option>泰迪</option><option>边牧</option><option>柴犬</option>
            <option>侏儒兔</option><option>仓鼠</option>
          </datalist>
        </div>
        <div class="field">
          <label>几岁</label>
          <input id="ageInput" maxlength="10" placeholder="2 岁" autocomplete="off" />
        </div>
      </div>

      <div class="field">
        <label>它的性格（可多选，也可以自己加）</label>
        <div class="chip-board" id="traitBoard">
          ${TRAIT_SAMPLES.map((t) => `<button class="chip" data-trait="${t}">${t}</button>`).join("")}
        </div>
      </div>

      <button class="primary" id="createBtn">给它做张人设卡</button>
      <button class="ghost" id="demoBtn">先看看示例：一只叫豆花的猫</button>
      <p class="hint">人设卡决定它说话的口气，之后每条动态都由 AI 按这个口气写</p>
    </div>
  `;

  document.getElementById("createBtn").addEventListener("click", createPet);
  document.getElementById("demoBtn").addEventListener("click", loadDemo);

  document.getElementById("traitBoard").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) chip.classList.toggle("on");
  });

  document.getElementById("nameInput").focus();
}

async function createPet() {
  const name = document.getElementById("nameInput").value.trim();
  const species = document.getElementById("speciesInput").value.trim() || "猫";
  const age = document.getElementById("ageInput").value.trim();
  const traits = [...document.querySelectorAll(".chip.on")]
    .map((el) => el.dataset.trait)
    .join(",");

  if (!name) {
    toast("先告诉它叫什么吧");
    document.getElementById("nameInput").focus();
    return;
  }

  const btn = document.getElementById("createBtn");
  btn.disabled = true;
  showBussy(`正在给「${name}」设计人设…`);
  try {
    await api("/api/pet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, species, age, traits }),
    });
    await loadState();
    toast(`「${name}」的人设卡做好了，发一条试试`);
  } catch (err) {
    toast(err.message);
  } finally {
    hideBussy();
    btn.disabled = false;
  }
}

async function loadDemo() {
  showBussy("正在翻它的历史动态…");
  try {
    state = await api("/api/demo", { method: "POST" });
    render();
    toast("这是豆花的第 24 条动态，往下翻翻");
  } catch (err) {
    toast(err.message);
  } finally {
    hideBussy();
  }
}

/* ------------------------------------------------------------ 渲染：主页 */

function heroHTML() {
  const pet = state.pet;
  const lv = pet.level;
  const st = state.stats;
  const stats = `${st.total_posts} 条动态 · ${st.total_likes} 个赞 · 陪了 ${daysTogether(state.posts)} 天`;
  const modeLabel = state.mode === "llm" ? "AI 在线" : "演示模式";

  return `
    <div class="hero">
      <div class="hero-top">
        <div class="avatar">${speciesEmoji(pet.species)}</div>
        <div style="flex:1;min-width:0">
          <div class="hero-name">
            ${esc(pet.name)}
            <span class="level-tag">Lv.${lv.index + 1} ${esc(lv.title)}</span>
          </div>
          <div class="hero-sub">${esc(pet.species)}${pet.age ? " · " + esc(pet.age) : ""} · 连续发了 ${pet.streak} 天</div>
          <div class="hero-tags">
            ${(pet.persona.tags || []).map((t) => `<span class="hero-tag">${esc(t)}</span>`).join("")}
            <span class="mode-badge ${state.mode === "llm" ? "" : "offline"}"><i></i>${modeLabel}</span>
          </div>
        </div>
      </div>
      <div class="exp-bar">
        <div class="exp-line">
          <span>${lv.next_title ? `距离「${lv.next_title}」还差 ${lv.to_next} 点` : "已经是这个家最大的一只了"}</span>
          <span>${lv.exp} exp</span>
        </div>
        <div class="exp-track"><div class="exp-fill" style="width:${lv.percent}%"></div></div>
      </div>
      <div class="hero-stats">${stats}</div>
    </div>
  `;
}

function postHTML(post, fresh = false) {
  const pet = state.pet;
  const likes = post.likes || [];
  const comments = post.comments || [];
  return `
    <article class="post ${fresh ? "fresh" : ""}" data-id="${post.id}">
      <div class="post-head">
        <div class="post-avatar">${speciesEmoji(pet.species)}</div>
        <div>
          <div class="post-who">${esc(pet.name)}</div>
          <div class="post-meta">${fmtTime(post.created_at)} · 来自爪机</div>
        </div>
      </div>
      <div class="post-body">${esc(post.caption)}</div>
      ${post.mood ? `<span class="mood"># ${esc(post.mood)}</span>` : ""}
      ${
        post.photo
          ? `<div class="photo"><img src="${esc(post.photo)}" alt="" loading="lazy" /></div>`
          : `<div class="photo-ph"><span>${speciesEmoji(pet.species)}</span>今天的长相，概不外借</div>`
      }
      <div class="post-foot">
        <span>${post.exp_gain ? `+${post.exp_gain} exp` : ""}</span>
        <div class="post-actions">
          <button data-act="save">存图</button>
        </div>
      </div>
      ${
        likes.length
          ? `<div class="likes">♡ <b>${likes.map(esc).join("、")}</b> 觉得这条还行</div>`
          : ""
      }
      <div class="comments">
        ${comments
          .map(
            (c, i) => `<div class="comment friend-${i}"><b>${esc(c.friend)}：</b>${esc(c.text)}</div>`
          )
          .join("")}
      </div>
    </article>
  `;
}

function render() {
  if (!state.pet) {
    renderWelcome();
    return;
  }

  const posts = state.posts || [];
  const banner = state.pet.is_demo
    ? `<div class="demo-banner">
         <span>这是示例 · 豆花的 ${posts.length} 条动态</span>
         <button id="bannerNew">换成我家那只 →</button>
       </div>`
    : "";

  screenEl.innerHTML = `
    ${heroHTML()}
    ${banner}
    <div class="feed" id="feed">
      ${
        posts.length
          ? posts.map((p) => postHTML(p)).join("")
          : `<div class="empty"><div class="empty-emoji">🐾</div>还没有动态。<br />点下面的按钮，让它发第一条。</div>`
      }
    </div>
    <div class="footer-note">
      ${esc(state.pet.name)}的朋友圈 · 由 AI 代笔
      <button class="footer-link" id="footerNew">换一只宠物</button>
    </div>
  `;

  fab.hidden = false;
  bindPostActions();

  document.getElementById("bannerNew")?.addEventListener("click", () => {
    // 示例数据本来就是给人看的，直接清掉不打断节奏
    startNewPet();
  });

  document.getElementById("footerNew")?.addEventListener("click", () => {
    if (!window.confirm("换宠物会清空当前这只的所有动态，确定吗？")) return;
    startNewPet();
  });
}

/** 清空当前数据，回到"给宠物建人设卡"的界面 */
async function startNewPet() {
  try {
    state = await api("/api/reset", { method: "POST" });
    render();
    toast("来，填一下你家那位的信息");
  } catch (err) {
    toast(err.message);
  }
}

function bindPostActions() {
  document.querySelectorAll(".post").forEach((node) => {
    node.querySelector('[data-act="save"]')?.addEventListener("click", () => savePost(node));
  });
}

async function savePost(node) {
  if (typeof html2canvas !== "function") {
    toast("截图保存吧：长按这条动态 → 保存图片");
    return;
  }
  try {
    const canvas = await html2canvas(node, {
      scale: 2,
      backgroundColor: "#ffffff",
      useCORS: true,
      logging: false,
    });
    const link = document.createElement("a");
    link.download = `${state.pet.name}-朋友圈-${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
    toast("存好了，去发吧");
  } catch {
    toast("截图保存吧：长按这条动态 → 保存图片");
  }
}

/* ------------------------------------------------------------ 发布 */

function openSheet() {
  sheet.hidden = false;
  eventInput.value = "";
  resetPhoto();
  eventInput.focus();
  document.getElementById("eventChips").innerHTML = EVENT_SAMPLES.map(
    (s) => `<button class="chip" data-sample="${s}">${s}</button>`
  ).join("");
}

function closeSheet() {
  sheet.hidden = true;
}

function resetPhoto() {
  currentFile = null;
  fileInput.value = "";
  preview.hidden = true;
  previewImg.removeAttribute("src");
}

async function submitPost() {
  const event = eventInput.value.trim();
  if (event.length < 2) {
    toast("多写两个字吧，AI 才好接梗");
    eventInput.focus();
    return;
  }

  const btn = document.getElementById("submitPost");
  btn.disabled = true;
  closeSheet();
  showBussy(`${state.pet.name}正在组织语言…`);

  const levelBefore = state.pet.level.index;

  try {
    let photo = "";
    if (currentFile) {
      const fd = new FormData();
      fd.append("file", currentFile);
      const up = await api("/api/upload", { method: "POST", body: fd });
      photo = up.url;
    }

    const res = await api("/api/post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, photo }),
    });

    state.posts.unshift(res.post);
    state.pet = res.pet;
    state.stats = res.stats;

    render();
    const first = document.querySelector(".post");
    if (first) {
      first.classList.add("fresh");
      setTimeout(() => first.classList.remove("fresh"), 3000);
    }

    if (res.offline && state.mode === "llm") {
      toast("模型这次没接上，用备用文案顶上了一条");
    } else if (res.pet.level.index > levelBefore) {
      toast(`升级了！现在是「${res.pet.level.title}」`);
    } else {
      toast(`+${res.exp_gain} exp`);
    }
  } catch (err) {
    toast(err.message);
  } finally {
    hideBussy();
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------ 事件绑定 */

fab.addEventListener("click", openSheet);

sheet.addEventListener("click", (e) => {
  if (e.target.dataset.close !== undefined) closeSheet();
});

document.getElementById("eventChips").addEventListener("click", (e) => {
  const chip = e.target.closest("[data-sample]");
  if (chip) {
    eventInput.value = chip.dataset.sample;
    eventInput.focus();
  }
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  currentFile = file;
  previewImg.src = URL.createObjectURL(file);
  preview.hidden = false;
});

document.getElementById("previewDel").addEventListener("click", resetPhoto);
document.getElementById("submitPost").addEventListener("click", submitPost);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSheet();
});

/* ------------------------------------------------------------ 启动 */

async function loadState() {
  state = await api("/api/state");
  render();
}

loadState().catch((err) => {
  screenEl.innerHTML = `<div class="empty"><div class="empty-emoji">😿</div>连接不上服务<br />${esc(
    err.message
  )}</div>`;
});
