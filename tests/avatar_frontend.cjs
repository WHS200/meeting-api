const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function environment() {
  const elements = new Map();
  const listeners = new Map();
  function element() {
    return {
      innerHTML: '', textContent: '', value: '', children: [], listeners: {},
      parentElement: { insertBefore() {} },
      addEventListener(type, callback) { this.listeners[type] = callback; },
      appendChild(child) { this.children.push(child); },
      prepend(child) { this.children.unshift(child); },
      querySelectorAll() { return []; },
    };
  }
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    querySelectorAll(selector) {
      return selector === '[data-user-initial]' ? [this.getElementById('headerAvatar')]
        : selector === '[data-user-nickname]' ? [this.getElementById('headerNickname')] : [];
    },
    addEventListener(type, callback, capture) { listeners.set(type, { callback, capture }); },
    createTextNode(value) { return { textContent: value }; },
    createElement: element,
  };
  const context = vm.createContext({
    document, location: { pathname: '/static/profile.html', search: '' },
    FormData: class { append() {} }, showToast() {}, URLSearchParams,
    apiFetch: async () => null,
  });
  function load(name) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js', name), 'utf8'), context);
  }
  load('common.js');
  return { context, document, listeners, load, run: code => vm.runInContext(code, context) };
}

async function testEscaping() {
  const env = environment();
  env.context.nickname = '\"><script>alert(1)</script>&\'';
  env.context.url = 'https://example.test/\" onerror=\"alert(2)&x=<tag>';
  const markup = env.run('avatarMarkup(url, nickname)');
  assert.ok(markup.includes('src="https://example.test/&quot; onerror=&quot;alert(2)&amp;x=&lt;tag&gt;"'));
  assert.ok(markup.includes('alt="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;&amp;&#039; 프로필"'));
  assert.ok(!markup.includes('<script>'));
  assert.equal(env.run('avatarContent(null, "김규민")'), '김');
  assert.equal(env.run('avatarContent("", "")'), '?');
  assert.equal(env.run('avatarContent(null, "😀name")'), '😀');
  assert.equal(env.run('avatarContent(null, "<name")'), '&lt;');
  env.load('feature-common.js');
  assert.ok(env.run('userLabel({user_id: 2, nickname, profile_image: url})').includes(markup));
}

async function testFailure() {
  const env = environment();
  const handler = env.listeners.get('error');
  assert.equal(handler.capture, true);
  let replacement;
  const img = {
    tagName: 'IMG', dataset: { avatarInitial: '<' },
    hasAttribute: name => name === 'data-avatar-initial',
    replaceWith: node => { replacement = node; },
  };
  handler.callback({ target: img });
  assert.equal(replacement.textContent, '<');
  img.dataset.avatarInitial = '';
  handler.callback({ target: img });
  assert.equal(replacement.textContent, '?');
  replacement = null;
  img.hasAttribute = () => false;
  handler.callback({ target: img });
  assert.equal(replacement, null);
}

async function testProfileRefresh() {
  const env = environment();
  let current = { user_id: 1, nickname: '김규민', profile_image: null };
  let reads = 0;
  env.context.apiFetch = async (url, options = {}) => {
    if (url === '/api/users/me/profile-image') {
      current = { ...current, profile_image: 'https://example.test/new.png' };
      return { message: 'Uploaded' };
    }
    if (url === '/api/users/me' && options.method === 'PATCH') {
      current = { ...current, nickname: JSON.parse(options.body).nickname };
      return { message: 'Updated' };
    }
    if (url === '/api/users/me') { reads++; return { ...current }; }
    return url === '/api/sports' ? [] : { sports: [] };
  };
  env.load('profile.js');
  await new Promise(resolve => setImmediate(resolve));
  const header = env.document.getElementById('headerAvatar');
  const body = env.document.getElementById('avatar');
  assert.equal(header.innerHTML, '김');
  assert.equal(body.innerHTML, header.innerHTML);
  assert.equal(reads, 1);
  await env.document.getElementById('imageForm').listeners.submit({
    preventDefault() {}, currentTarget: { profile_image: { files: [{}] } },
  });
  assert.equal(reads, 2);
  assert.ok(header.innerHTML.includes('https://example.test/new.png'));
  assert.equal(body.innerHTML, header.innerHTML);
  assert.equal((await env.run('getCurrentUser()')).profile_image, current.profile_image);
  assert.equal(reads, 2);
  await env.document.getElementById('profileForm').listeners.submit({
    preventDefault() {}, currentTarget: { nickname: { value: '변경' }, region: { value: 'Seoul' } },
  });
  assert.equal(reads, 3);
  assert.equal(env.document.getElementById('headerNickname').textContent, '변경');
  assert.equal(body.innerHTML, header.innerHTML);
}

async function testChat() {
  const env = environment();
  env.load('chat.js');
  await new Promise(resolve => setImmediate(resolve));
  env.run('me = {nickname: "나"}; renderMembers([{nickname: "김규민", profile_image: "/uploads/member.png"}, {nickname: "박민수"}])');
  const members = env.document.getElementById('memberList').innerHTML;
  assert.ok(members.includes('/uploads/member.png'));
  assert.ok(members.includes('>박</span>'));
  assert.ok(env.run('roomButton({room_type: "DIRECT", chat_room_id: 1, direct_nickname: "김규민", direct_profile_image: "/uploads/direct.png"})').includes('/uploads/direct.png'));
  assert.ok(env.run('roomButton({room_type: "DIRECT", chat_room_id: 1, direct_nickname: "김규민"})').includes('class="avatar">김</div>'));
  assert.ok(env.run('roomButton({room_type: "DIRECT", chat_room_id: 1})').includes('class="avatar">?</div>'));
  env.run('appendMessage({message_id: 1, sender_id: 2, sender_nickname: "김규민", sender_profile_image: "/uploads/sender.png", content: "<script>bad</script>"}, true)');
  env.run('appendMessage({message_id: 2, sender_id: 3, sender_nickname: "박민수", content: "live"})');
  env.run('appendMessage({message_id: 3, sender_id: 1, sender_nickname: "나", content: "mine"})');
  const messages = env.document.getElementById('messages').children;
  assert.ok(messages[0].innerHTML.includes('/uploads/sender.png'));
  assert.ok(messages[0].innerHTML.includes('&lt;script&gt;bad&lt;/script&gt;'));
  assert.ok(messages[1].innerHTML.includes('>박</a>'));
  assert.ok(!messages[2].innerHTML.includes('chat-profile-avatar'));
}

const tests = { escaping: testEscaping, failure: testFailure, profile: testProfileRefresh, chat: testChat };
tests[process.argv[2]]().catch(error => { console.error(error); process.exitCode = 1; });
