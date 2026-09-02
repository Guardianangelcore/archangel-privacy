#!/usr/bin/env node
/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// i18n CODEMOD — externalises hard-coded UI strings of a screen into src/locales/en.json and
// rewrites the source to `tt('screen.key')` (tt = useI18n().t alias, injected per component).
//
//   node scripts/i18n-codemod.js [--write] app/subscription.tsx app/meds.tsx ...
//
// Precise range-based edits (no reprinting) so formatting/diffs stay minimal. What it translates:
//   • JSXText with ≥2 letters                         → {tt('k')}
//   • {'literal'} / {a ? 'x' : 'y'} / {a || 'x'} children → tt('k')
//   • {`Text ${expr}`} children                      → tt('k', [expr])   (key text uses {0},{1}…)
//   • attributes placeholder/title/label/…            → {tt('k')}
//   • options={{ title: 'x' }} / Alert.alert('t','m') → tt('k')
// Skipped (reported): strings outside any JSX-rendering function (module-level constants),
// short codes (GA-T, OK, SOS…), URLs, template-only-expressions.
const fs = require('fs');
const path = require('path');
const parser = require('@babel/parser');
const traverse = require('@babel/traverse').default;

const ROOT = path.resolve(__dirname, '..');
const LOCALE_PATH = path.join(ROOT, 'src/locales/en.json');
const REPORT_PATH = path.join(ROOT, 'src/locales/_codemod_report.json');
const WRITE = process.argv.includes('--write');
const files = process.argv.slice(2).filter(a => !a.startsWith('--'));

const ATTRS = new Set(['placeholder', 'title', 'label', 'subtitle', 'description', 'hint', 'message', 'accessibilityLabel',
  'accessibilityHint', 'emptyTitle', 'emptySub', 'cta', 'headerTitle', 'tagline', 'caption', 'sublabel', 'helper', 'eyebrow']);
const OBJ_KEYS = new Set(['title', 'label', 'subtitle', 'description', 'hint', 'message', 'headerTitle', 'placeholder', 'text',
  'desc', 'sub', 'cta', 'tagline', 'headline', 'body', 'caption', 'question', 'answer', 'tip', 'note']);
const HAS_LETTERS = /\p{L}.*\p{L}/su;                 // at least two letters anywhere
const SHORT_CODE = /^[A-Z0-9€$%+\-_.:/·•]{1,5}$/;      // GA-T, SOS, OK, EUR, P1M …
const SKIP_RE = /https?:\/\/|@\w+\.\w+|^\s*[\d.,%€$+\-–—/·•:]*\s*$/;

const enJson = fs.existsSync(LOCALE_PATH) ? JSON.parse(fs.readFileSync(LOCALE_PATH, 'utf8')) : {};
const report = fs.existsSync(REPORT_PATH) ? JSON.parse(fs.readFileSync(REPORT_PATH, 'utf8')) : {};
const textToKey = new Map(Object.entries(enJson).map(([k, v]) => [`${k.split('.')[0]}\u0000${v}`, k]));

function screenName(file) {
  const rel = path.relative(ROOT, file).replace(/\\/g, '/');
  return rel.replace(/^app\//, '').replace(/^src\//, 'c_').replace(/\(tabs\)\//, 'tabs_').replace(/\.tsx?$/, '').replace(/[^a-zA-Z0-9]+/g, '_');
}

function slugify(text) {
  const s = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/\{\d+\}/g, ' ').replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return (s || 'txt').slice(0, 36).replace(/_+$/g, '');
}

function hash(s) { let h = 5381; for (const c of s) h = ((h << 5) + h + c.codePointAt(0)) >>> 0; return h.toString(36).slice(0, 4); }

function keyFor(screen, text) {
  const id = `${screen}\u0000${text}`;
  if (textToKey.has(id)) return textToKey.get(id);
  let key = `${screen}.${slugify(text)}`;
  if (enJson[key] !== undefined && enJson[key] !== text) key = `${key}_${hash(text)}`;
  enJson[key] = text;
  textToKey.set(id, key);
  return key;
}

function translatable(text) {
  const tr = text.trim();
  if (!tr || !HAS_LETTERS.test(tr) || SKIP_RE.test(tr)) return false;
  if (SHORT_CODE.test(tr)) return false;
  if (/^[a-z0-9_]+$/.test(tr) && /_/.test(tr)) return false; // identifiers like some_key
  return true;
}

// Outermost function ancestor (component). Returns path or null.
function outermostFunction(p) {
  let fn = null, cur = p;
  while (cur) { if (cur.isFunction()) fn = cur; cur = cur.parentPath; }
  return fn;
}
function containsJSX(fnPath) {
  let found = false;
  fnPath.traverse({ JSXElement() { found = true; }, JSXFragment() { found = true; } });
  return found;
}

// Is the string literal / template a "direct" JSX child expression (only through ?:, ||/??, +, parens)?
function jsxChildExprAncestor(p) {
  let cur = p;
  while (cur && cur.parentPath) {
    const par = cur.parentPath;
    if (par.isJSXExpressionContainer()) return par.parentPath && (par.parentPath.isJSXElement() || par.parentPath.isJSXFragment()) ? par : null;
    if (par.isConditionalExpression() && cur.key !== 'test') { cur = par; continue; }
    if (par.isLogicalExpression()) { cur = par; continue; }
    if (par.isBinaryExpression() && par.node.operator === '+') { cur = par; continue; }
    if (par.isParenthesizedExpression() || par.isTSAsExpression()) { cur = par; continue; }
    return null;
  }
  return null;
}

function processFile(file) {
  const abs = path.resolve(ROOT, file);
  const src = fs.readFileSync(abs, 'utf8');
  const screen = screenName(abs);
  let ast;
  try {
    ast = parser.parse(src, { sourceType: 'module', plugins: ['jsx', 'typescript'], ranges: true });
  } catch (e) { console.error(`✗ parse ${file}: ${e.message}`); return; }

  const edits = [];               // {start, end, text}
  const skipped = [];
  const hookFns = new Map();      // fn node -> path (functions needing `tt`)
  const q = s => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
  // tt() call for a string literal, keeping the literal's own leading/trailing spaces (e.g. '  ✓ ACTIVE')
  const lit = (key, v) => {
    const lead = v.match(/^\s*/)[0], trail = v.match(/\s*$/)[0];
    return `${lead ? q(lead) + ' + ' : ''}tt(${q(key)})${trail ? ' + ' + q(trail) : ''}`;
  };

  function claim(p, text) {
    const fn = outermostFunction(p);
    if (!fn || !containsJSX(fn)) { skipped.push(text.trim()); return null; }
    hookFns.set(fn.node, fn);
    return keyFor(screen, text.trim());
  }

  traverse(ast, {
    JSXText(p) {
      const raw = p.node.value;
      if (!translatable(raw)) return;
      const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0];
      const core = raw.slice(lead.length, raw.length - trail.length).replace(/\s+/g, ' ');
      const key = claim(p, core);
      if (!key) return;
      edits.push({ start: p.node.start + lead.length, end: p.node.end - trail.length, text: `{tt(${q(key)})}` });
    },
    StringLiteral(p) {
      const v = p.node.value;
      if (!translatable(v)) return;
      const par = p.parentPath;
      // attribute="text"
      if (par.isJSXAttribute() && ATTRS.has(par.node.name.name)) {
        const key = claim(p, v); if (!key) return;
        edits.push({ start: p.node.start, end: p.node.end, text: `{${lit(key, v)}}` }); return;
      }
      // object property inside a JSX attribute or Alert.alert(...)
      if (par.isObjectProperty() && par.node.value === p.node && !par.node.computed) {
        const kname = par.node.key.name || par.node.key.value;
        if (OBJ_KEYS.has(kname) && (p.findParent(a => a.isJSXAttribute()) || p.findParent(a => a.isCallExpression() && isAlert(a.node)))) {
          const key = claim(p, v); if (!key) return;
          edits.push({ start: p.node.start, end: p.node.end, text: lit(key, v) });
        }
        return;
      }
      // Alert.alert('title', 'message')
      if (par.isCallExpression() && isAlert(par.node) && par.node.arguments.indexOf(p.node) <= 1) {
        const key = claim(p, v); if (!key) return;
        edits.push({ start: p.node.start, end: p.node.end, text: lit(key, v) }); return;
      }
      // {'text'} / {a ? 'x' : 'y'} / {a || 'x'} as JSX child; also the same shapes inside translatable attributes
      const container = jsxChildExprAncestor(p);
      const attr = p.findParent(a => a.isJSXAttribute());
      if (container || (attr && ATTRS.has(attr.node.name.name) && jsxAttrExpr(p))) {
        const key = claim(p, v); if (!key) return;
        edits.push({ start: p.node.start, end: p.node.end, text: lit(key, v) });
      }
    },
    TemplateLiteral(p) {
      if (p.parentPath.isTaggedTemplateExpression()) return;
      const container = jsxChildExprAncestor(p);
      const attr = p.findParent(a => a.isJSXAttribute());
      if (!container && !(attr && ATTRS.has(attr.node.name.name) && jsxAttrExpr(p))) return;
      const quasis = p.node.quasis.map(qq => qq.value.cooked ?? '');
      const joined = quasis.join(' ');
      if (!translatable(joined)) return;
      const exprs = p.node.expressions.map(e => src.slice(e.start, e.end));
      const text = quasis.map((s, i) => s + (i < exprs.length ? `{${i}}` : '')).join('').replace(/\s+/g, ' ').trim();
      const key = claim(p, text); if (!key) return;
      edits.push({ start: p.node.start, end: p.node.end, text: exprs.length ? `tt(${q(key)}, [${exprs.join(', ')}])` : `tt(${q(key)})` });
    },
  });

  function isAlert(call) {
    const c = call.callee;
    return c && c.type === 'MemberExpression' && c.object.name === 'Alert' && c.property.name === 'alert';
  }
  function jsxAttrExpr(p) { // literal reachable from the attribute's expression container through ?:/||/+ only
    let cur = p;
    while (cur && cur.parentPath) {
      const par = cur.parentPath;
      if (par.isJSXExpressionContainer()) return true;
      if ((par.isConditionalExpression() && cur.key !== 'test') || par.isLogicalExpression() ||
          (par.isBinaryExpression() && par.node.operator === '+') || par.isParenthesizedExpression()) { cur = par; continue; }
      return false;
    }
    return false;
  }

  if (!edits.length) { report[screen] = { translated: 0, skipped }; console.log(`· ${file}: nothing to do (${skipped.length} skipped)`); return; }

  // Hook injection per component
  for (const [, fnPath] of hookFns) {
    const body = fnPath.node.body;
    const bodySrc = src.slice(fnPath.node.start, fnPath.node.end);
    if (/const\s*\{[^}]*\bt\s*:\s*tt\b[^}]*\}\s*=\s*useI18n\(\)/.test(bodySrc)) continue; // already has tt
    if (body.type === 'BlockStatement') {
      edits.push({ start: body.start + 1, end: body.start + 1, text: `\n  const { t: tt } = useI18n();` });
    } else {
      edits.push({ start: body.start, end: body.start, text: `{ const { t: tt } = useI18n(); return (` });
      edits.push({ start: body.end, end: body.end, text: `); }` });
    }
  }
  // Import injection
  if (!/useI18n/.test(src.split('\n').filter(l => l.startsWith('import')).join('\n'))) {
    const imports = ast.program.body.filter(n => n.type === 'ImportDeclaration');
    const last = imports[imports.length - 1];
    edits.push({ start: last.end, end: last.end, text: `\nimport { useI18n } from '@/src/i18n-context';` });
  }

  // Apply edits back-to-front (inserts at the same position: hook/import first is fine)
  edits.sort((a, b) => b.start - a.start || b.end - a.end);
  let out = src;
  for (const e of edits) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const n = edits.filter(e => e.text.includes('tt(')).length;
  report[screen] = { translated: n, skipped };
  console.log(`${WRITE ? '✔' : '○'} ${file}: ${n} strings → tt(), ${hookFns.size} component(s), ${skipped.length} skipped`);
  if (WRITE) fs.writeFileSync(abs, out);
}

files.forEach(processFile);
if (WRITE) {
  fs.mkdirSync(path.dirname(LOCALE_PATH), { recursive: true });
  const sorted = Object.fromEntries(Object.entries(enJson).sort(([a], [b]) => a.localeCompare(b)));
  fs.writeFileSync(LOCALE_PATH, JSON.stringify(sorted, null, 2) + '\n');
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2) + '\n');
  console.log(`en.json: ${Object.keys(sorted).length} keys`);
}
