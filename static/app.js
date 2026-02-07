const GUEST = new URLSearchParams(window.location.search).get('guest') === '1';
const TOKEN_KEY = 'rag_token';

const authView = document.getElementById('auth');
const chatView = document.getElementById('chat');
const userSpan = document.getElementById('user');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const messages = document.getElementById('messages');
const questionInput = document.getElementById('question');
const sendBtn = document.getElementById('sendBtn');

const nowTs = () => new Date().toLocaleTimeString();

const api = (path, options = {}) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(path, { ...options, headers });
};

const renderUserMsg = (text, ts) => {
  const wrap = document.createElement('div');
  wrap.className = 'msg user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const t = document.createElement('div');
  t.className = 'text';
  t.textContent = text;
  const m = document.createElement('div');
  m.className = 'meta';
  m.textContent = ts || nowTs();
  bubble.appendChild(t);
  bubble.appendChild(m);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
};

const renderBotMsg = (text, ts) => {
  const wrap = document.createElement('div');
  wrap.className = 'msg bot';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = 'AI';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const t = document.createElement('div');
  t.className = 'text';
  t.textContent = text;
  const m = document.createElement('div');
  m.className = 'meta';
  m.textContent = ts || nowTs();
  bubble.appendChild(t);
  bubble.appendChild(m);
  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
};

const renderBotLoading = () => {
  const wrap = document.createElement('div');
  wrap.className = 'msg bot loading';
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = 'AI';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const t = document.createElement('div');
  t.className = 'text';
  t.innerHTML = '<span class="spinner"></span>正在生成...';
  const m = document.createElement('div');
  m.className = 'meta';
  m.textContent = nowTs();
  bubble.appendChild(t);
  bubble.appendChild(m);
  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
  return { wrap, bubble, t };
};

const typeText = async (el, text) => {
  el.textContent = '';
  for (let i = 0; i < text.length; i++) {
    el.textContent += text[i];
    await new Promise(r => setTimeout(r, 8));
  }
};

const saveChat = async (question, answer, error) => {
  if (GUEST) return;
  try {
    await api('/chats', {
      method: 'POST',
      body: JSON.stringify({ question, answer: answer || '', error: error || '' })
    });
  } catch {}
};

document.getElementById('signin').addEventListener('click', async () => {
  const email = emailInput.value.trim();
  const password = passwordInput.value.trim();
  if (!email || !password) return;
  try {
    const r = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Login failed');
    localStorage.setItem(TOKEN_KEY, data.token);
    userSpan.textContent = data.user?.email || email;
    authView.classList.add('hidden');
    chatView.classList.remove('hidden');
    loadHistory();
  } catch (err) {
    alert(err.message || 'Login failed');
  }
});

document.getElementById('signup').addEventListener('click', async () => {
  const email = emailInput.value.trim();
  const password = passwordInput.value.trim();
  if (!email || !password) return;
  try {
    const r = await api('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Signup failed');
    localStorage.setItem(TOKEN_KEY, data.token);
    userSpan.textContent = data.user?.email || email;
    authView.classList.add('hidden');
    chatView.classList.remove('hidden');
  } catch (err) {
    alert(err.message || 'Signup failed');
  }
});

document.getElementById('signout').addEventListener('click', () => {
  if (GUEST) return;
  localStorage.removeItem(TOKEN_KEY);
  userSpan.textContent = '';
  authView.classList.remove('hidden');
  chatView.classList.add('hidden');
  messages.innerHTML = '';
});

const checkAuth = async () => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    authView.classList.remove('hidden');
    chatView.classList.add('hidden');
    return;
  }
  try {
    const r = await api('/auth/me');
    if (!r.ok) throw new Error();
    const data = await r.json();
    userSpan.textContent = data.email || data.id;
    authView.classList.add('hidden');
    chatView.classList.remove('hidden');
    loadHistory();
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    authView.classList.remove('hidden');
    chatView.classList.add('hidden');
  }
};

if (GUEST) {
  userSpan.textContent = 'Guest';
  authView.classList.add('hidden');
  chatView.classList.remove('hidden');
  document.getElementById('signout').style.display = 'none';
} else {
  fetch('/api/status').then(r => r.json()).then(s => {
    if (!s.mongo) {
      const msg = document.createElement('div');
      msg.style.cssText = 'padding:12px;background:#f44336;color:white;text-align:center;';
      msg.textContent = 'Database not configured. Please add MONGODB_URI in Railway.';
      document.querySelector('.content').insertBefore(msg, document.querySelector('.content').firstChild);
    }
  }).catch(() => {});
  checkAuth();
}

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = questionInput.value.trim();
  if (!q) return;
  renderUserMsg(q);
  questionInput.value = '';
  sendBtn.disabled = true;
  sendBtn.textContent = '发送中...';
  questionInput.disabled = true;
  const { wrap, bubble, t } = renderBotLoading();
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const data = await res.json();
    const body = Array.isArray(data) ? (data[0] || {}) : data;
    const text = body.answer || body.error || '请求失败';
    wrap.classList.remove('loading');
    await typeText(t, text);
    await saveChat(q, body.answer || '', body.error || '');
  } catch (err) {
    wrap.classList.remove('loading');
    const msg = '请求错误';
    t.textContent = msg;
    await saveChat(q, '', msg);
  }
  sendBtn.disabled = false;
  sendBtn.textContent = '发送';
  questionInput.disabled = false;
});

const loadHistory = async () => {
  if (GUEST) return;
  messages.innerHTML = '';
  try {
    const r = await api('/chats');
    if (!r.ok) return;
    const data = await r.json();
    (data.chats || []).forEach(d => {
      const ts = d.createdAt ? new Date(d.createdAt).toLocaleTimeString() : nowTs();
      if (d.question) renderUserMsg(d.question, ts);
      const text = d.answer || d.error || '';
      if (text) renderBotMsg(text, ts);
    });
  } catch {}
};
