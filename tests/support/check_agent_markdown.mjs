// Run with: node tests/support/check_agent_markdown.mjs /path/to/frontend-with-node_modules
// Uses the actual component source from the generator template; no model or backend required.
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const project = resolve(process.argv[2]);
const require = createRequire(resolve(project, 'package.json'));
const { build } = require('esbuild');
const source = readFileSync(fileURLToPath(new URL('../../src/onesite/templates/codegen/agent_page.tsx.j2', import.meta.url)), 'utf8');
const imports = source.slice(source.indexOf('import React,'), source.indexOf('import request,'));
const components = source.slice(source.indexOf('function CodeBlock('), source.indexOf('function ToolActivity('));
writeFileSync(resolve(project, 'markdown-components.tsx'), imports + components + '\nexport { MarkdownMessage };\n');
writeFileSync(resolve(project, 'markdown-check.tsx'), `
import React from 'react';
import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { MarkdownMessage } from './markdown-components';
async function main() {
  await i18n.use(initReactI18next).init({ lng: 'en', resources: { en: { translation: {} } } });
  const content = [
    '# Heading', '', 'Text with **bold**, *emphasis*, ~~removed~~ and \`inline\`.', '',
    '| Name | Value |', '| :--- | ---: |', '| Alpha | 42 |', '',
    '- [x] Complete', '- [ ] Pending', '  - Nested', '',
    '3. Third', '4. Fourth', '', '> Quoted text', '', '---', '',
    '\`\`\`python', 'def hello():', '    return "world"', '\`\`\`', '',
    '\`\`\`unknown-language', '<script>alert(1)</script>', '\`\`\`', '',
    '[Website](https://example.com "Title")', '',
    '[Unsafe](javascript:alert%281%29)', '', '<script>alert(2)</script>', '',
    '![Example](https://example.com/image.png)',
  ].join('\\n');
  const html = renderToStaticMarkup(<MarkdownMessage content={content} />);
  assert.match(html, /<h1>Heading<\\/h1>/);
  assert.match(html, /<strong>bold<\\/strong>/);
  assert.match(html, /<del>removed<\\/del>/);
  assert.match(html, /<table /);
  assert.match(html, /text-align:right/);
  assert.match(html, /type="checkbox"/);
  assert.match(html, /disabled=""/);
  assert.match(html, /<ol start="3">/);
  assert.match(html, /hljs-keyword/);
  assert.match(html, /    <span class="hljs-keyword">return/);
  assert.match(html, /unknown-language/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script/);
  assert.doesNotMatch(html, /href="javascript:/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /loading="lazy"/);
  assert.match(html, /aria-label="Copy code"/);
  assert.match(html, /overflow-x-auto/);
  console.log('Markdown render checks passed: GFM, highlighting, whitespace, links and HTML handling.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
`);
await build({ entryPoints: [resolve(project, 'markdown-check.tsx')], outfile: resolve(project, 'markdown-check.cjs'), bundle: true, platform: 'node', format: 'cjs', logLevel: 'warning' });
execFileSync(process.execPath, [resolve(project, 'markdown-check.cjs')], { stdio: 'inherit' });
