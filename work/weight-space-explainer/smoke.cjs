const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(`${__dirname}/explanation.html`, 'utf8');
const elements = new Map();
for (const match of html.matchAll(/id="([^"]+)"/g)) {
  assert(!elements.has('#' + match[1]), 'Duplicate element ID');
  elements.set('#' + match[1], { value: '', textContent: '', handlers: {}, style: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    setAttribute(name, value) { this[name] = value; }
  });
}
for (const selector of ['.ball', '.paddle', '.court']) {
  elements.set(selector, { style: {}, setAttribute(name, value) { this[name] = value; } });
}
const get = id => elements.get('#' + id);
get('ball-position').value = '7';
get('paddle-position').value = '4';
get('note-section').value = '3. How can numbers express a rule?';
get('weight-space-explanation').querySelector = selector => {
  assert(elements.has(selector), `Missing element ${selector}`);
  return elements.get(selector);
};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], {
  document: { getElementById: get }
});
for (let ball = 0; ball <= 9; ball++) {
  for (let paddle = 0; paddle <= 9; paddle++) {
    get('ball-position').value = String(ball);
    get('paddle-position').value = String(paddle);
    get('ball-position').handlers.input();
    const expected = ball > paddle ? 'Move right' : ball < paddle ? 'Move left' : 'Stay';
    assert.equal(get('code-choice').textContent, expected);
    assert.equal(get('network-choice').textContent, expected);
    assert.equal(get('ball-value').textContent, ball);
    assert.equal(get('paddle-value').textContent, paddle);
    assert.equal(get('scores').textContent, `Right ${ball - paddle} · Left ${paddle - ball} · Stay 0`);
  }
}
get('note-text').value = ' ';
get('add-note').handlers.click();
assert.equal(get('prepared-feedback').value, '');
for (const note of ['Explain the negative weights.', '<script>literal note</script>']) {
  get('note-text').value = note;
  get('add-note').handlers.click();
  assert(get('prepared-feedback').value.includes(note));
  assert.equal(get('note-text').value, '');
}
console.log('PASS: all 100 position pairs, tied scores, slider updates, empty notes and multiple section notes.');
