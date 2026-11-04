// Execute the real generated component, keeping browser/framework details out of
// the test while exercising its public controls and asynchronous service calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require(process.argv[2]);
const compiled = ts.transpileModule(fs.readFileSync(process.argv[3], 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
  reportDiagnostics: true,
});
assert.equal(compiled.diagnostics.length, 0);
const copy = value => JSON.parse(JSON.stringify(value));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
};
const entry = (id, title, condition = true) => ({
  nodeid: `ns=2;s=${id}`, stable_nodeid: `nsu=urn:test;s=${id}`, title,
  node_class: condition ? 'Object' : 'Variable', is_condition: condition,
});
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...nodes(tree.props?.children)];
}
function content(tree) {
  if (Array.isArray(tree)) return tree.map(content).join('');
  if (tree == null || typeof tree === 'boolean') return '';
  return typeof tree === 'object' ? content(tree.props?.children) : String(tree);
}
function setup(options = {}) {
  const hooks = [], effects = [], requests = [], acWrites = [], nodeWrites = [], toasts = [];
  let cursor = 0, dirty = true, tree, added = 0;
  const acs = copy(options.acs || []), configuredNodes = [];
  const api = {discover: async () => ({items: options.conditions || []}), failConditions: new Set()};
  const equal = (a, b) => a && b && a.length === b.length && a.every((value, i) => Object.is(value, b[i]));
  const react = {
    useState(initial) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = typeof initial === 'function' ? initial() : initial;
      return [hooks[index], next => {
        const value = typeof next === 'function' ? next(hooks[index]) : next;
        if (!Object.is(value, hooks[index])) { hooks[index] = value; dirty = true; }
      }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = {current: initial};
      return hooks[index];
    },
    useCallback(fn, deps) {
      const index = cursor++;
      if (!hooks[index] || !equal(hooks[index].deps, deps)) hooks[index] = {fn, deps};
      return hooks[index].fn;
    },
    useEffect(fn, deps) {
      const index = cursor++;
      if (!hooks[index] || !equal(hooks[index].deps, deps)) {
        hooks[index] = {deps};
        effects.push(fn);
      }
    },
  };
  const request = {get: async (url, config) => {
    requests.push({url, config});
    if (url.endsWith('/conditions')) return {data: await api.discover()};
    return {data: {items: config.params.nodeid === 'i=85' ? (options.browse || []) : []}};
  }};
  const services = {
    getOpcuaNodes: async (page, size, filters) => {
      assert.equal(filters.opcua_server_id, 42);
      return {items: copy(configuredNodes)};
    },
    getOpcuaAcs: async (page, size, filters) => {
      assert.equal(filters.opcua_server_id, 42);
      if (options.configError) throw new Error('Configuration unavailable');
      return {items: copy(acs)};
    },
    createOpcuaNode: async value => {
      nodeWrites.push(copy(value));
      const record = {id: configuredNodes.length + 1, ...value};
      configuredNodes.push(record);
      return record;
    },
    createOpcuaAc: async value => {
      acWrites.push(copy(value));
      if (api.failConditions.has(value.condition_id)) throw new Error('Retry this condition');
      const record = {id: acs.length + 1, ...value};
      acs.push(record);
      return record;
    },
  };
  const modules = {
    react,
    'react/jsx-runtime': {jsx: (type, props) => ({type, props}), jsxs: (type, props) => ({type, props}), Fragment: 'Fragment'},
    'lucide-react': new Proxy({}, {get: (_, key) => String(key)}),
    sonner: {toast: new Proxy({}, {get: (_, level) => message => toasts.push({level, message})})},
    '../../utils/request': {default: request, getErrorMessage: (error, fallback) => error?.message || fallback},
    '../../components/ui/button': {Button: 'Button'},
    '../../components/ui/input': {Input: 'Input'},
    '../../components/ui/dialog': {Dialog: 'Dialog', DialogContent: 'DialogContent', DialogDescription: 'DialogDescription', DialogTitle: 'DialogTitle'},
    '../../services/opcua_node': services,
    '../../services/opcua_ac': services,
  };
  const exports = {};
  vm.runInNewContext(compiled.outputText, {exports, console, require: name => {
    assert.ok(name in modules, `Unexpected import ${name}`);
    return modules[name];
  }});
  const props = {
    serverId: 42, serverTitle: 'Test server', open: true, onOpenChange() {}, onRestoreFocus() {},
    onAdded: () => added++, canReadNodes: true, canAddNodes: true, canReadAcs: true, canAddAcs: true,
    ...options.props,
  };
  function render() {
    cursor = 0; dirty = false;
    tree = exports.default(props);
    effects.splice(0).forEach(fn => fn());
    return tree;
  }
  async function flush() {
    for (let i = 0; i < 12; i++) {
      if (dirty) render();
      await new Promise(resolve => setImmediate(resolve));
    }
    if (dirty) render();
  }
  const button = text => nodes(tree).find(node => ['Button', 'button'].includes(node.type) && content(node).includes(text));
  const byLabel = label => nodes(tree).find(node => node.props?.['aria-label'] === label || node.props?.label === label);
  return {api, requests, acWrites, nodeWrites, toasts, flush, button, byLabel,
    get tree() {return tree;}, get added() {return added;}};
}

async function main() {
  const existing = entry('existing', 'Existing alarm');
  const fresh = entry('fresh', 'Nested alarm');
  const failed = entry('failed', 'Retry alarm');
  const variable = entry('temperature', 'Temperature', false);
  {
    const x = setup({browse: [variable], acs: [
      {id: 1, condition_id: existing.nodeid, event_notifier_nodeid: 'ns=0;i=2253'},
      {id: 2, condition_id: fresh.stable_nodeid, event_notifier_nodeid: 'ns=2;s=OtherEvents'},
    ]});
    await x.flush();
    x.byLabel('选择 Temperature').props.onChange();
    await x.flush();
    const scan = deferred();
    x.api.discover = () => scan.promise;
    x.api.failConditions.add(failed.stable_nodeid);
    const bulk = x.button('一键导入所有 A&C');
    assert.ok(bulk && !bulk.props.disabled);
    bulk.props.onClick();
    bulk.props.onClick(); // A fast second click before React rerenders must be ignored.
    await x.flush();
    const scans = x.requests.filter(call => call.url.endsWith('/conditions'));
    assert.equal(scans.length, 1);
    assert.ok(scans[0].config.timeout >= 125000, 'discovery can outlast the normal request timeout');
    assert.equal(x.nodeWrites.length + x.acWrites.length, 0, 'wait for complete discovery before creating records');
    assert.match(content(x.tree), /正在.*(?:查找|扫描)/);
    scan.resolve({items: [existing, fresh, {...fresh}, failed, variable]});
    await x.flush();
    assert.deepEqual(x.acWrites.map(row => row.condition_id), [fresh.stable_nodeid, failed.stable_nodeid]);
    assert.equal(x.nodeWrites.length, 0, 'bulk AC import must not submit preselected variables');
    assert.ok(x.acWrites.every(row => row.opcua_server_id === 42 && row.event_notifier_nodeid === 'i=2253' && row.is_enabled));
    assert.equal(x.added, 1);
    assert.ok(x.byLabel('移除 Temperature'), 'the user\'s ordinary selection is retained');
    assert.ok(x.byLabel('移除 Retry alarm'), 'failed conditions are retained for manual retry');
    assert.equal(x.byLabel('移除 Nested alarm'), undefined);
    assert.match(content(x.tree), /跳过 1 个已添加项/);
    x.api.failConditions.clear();
    x.button('添加到服务器').props.onClick();
    await x.flush();
    assert.equal(x.requests.filter(call => call.url.endsWith('/conditions')).length, 1);
    assert.deepEqual(x.nodeWrites.map(row => row.nodeid), [variable.stable_nodeid]);
    assert.deepEqual(x.acWrites.map(row => row.condition_id), [fresh.stable_nodeid, failed.stable_nodeid, failed.stable_nodeid]);
    assert.equal(x.byLabel('移除 Retry alarm'), undefined);
    assert.equal(x.byLabel('移除 Temperature'), undefined);
    assert.equal(x.added, 2);
    x.button('一键导入所有 A&C').props.onClick();
    await x.flush();
    assert.equal(x.acWrites.length, 3, 'repeating a completed import must not create duplicates');
    assert.equal(x.nodeWrites.length, 1);
    assert.equal(x.added, 2);
    assert.match(content(x.tree), /跳过 3 个已添加项/);
  }
  // Empty discovery and discovery failure must leave ordinary selections alone.
  for (const fail of [false, true]) {
    const x = setup({browse: [variable]});
    await x.flush();
    x.byLabel('选择 Temperature').props.onChange();
    await x.flush();
    x.api.discover = async () => {if (fail) throw new Error('Discovery unavailable'); return {items: []};};
    x.button('一键导入所有 A&C').props.onClick();
    await x.flush();
    assert.equal(x.nodeWrites.length + x.acWrites.length, 0);
    assert.ok(x.byLabel('移除 Temperature'));
    assert.equal(x.added, 0);
    assert.ok(!x.button('一键导入所有 A&C').props.disabled);
    assert.match(content(x.tree), fail ? /Discovery unavailable/ : /没有|未发现|未找到/);
  }
  for (const props of [{canReadAcs: false}, {canAddAcs: false}]) {
    const x = setup({props});
    await x.flush();
    const bulk = x.button('一键导入所有 A&C');
    assert.ok(!bulk || bulk.props.disabled, 'bulk import requires read and create permissions');
  }
  {
    const x = setup({configError: true});
    await x.flush();
    assert.ok(x.button('一键导入所有 A&C').props.disabled, 'failed duplicate checks must block import');
  }
  // The chosen event subscription entry applies to every discovered condition.
  {
    const x = setup({conditions: [fresh], props: {canReadNodes: false, canAddNodes: false}});
    await x.flush();
    const notifier = nodes(x.tree).find(node => node.type === 'Input' && node.props.id === 'notifier-42');
    assert.ok(notifier, 'event entry must be editable before selecting any AC');
    notifier.props.onChange({target: {value: '  '}});
    await x.flush();
    assert.ok(x.button('一键导入所有 A&C').props.disabled, 'an event subscription entry is required');
    notifier.props.onChange({target: {value: '  ns=2;s=Events  '}});
    await x.flush();
    x.button('一键导入所有 A&C').props.onClick();
    await x.flush();
    assert.equal(x.acWrites[0].event_notifier_nodeid, 'ns=2;s=Events');
    assert.equal(x.nodeWrites.length, 0);
  }
  console.log('BrowsePanel bulk discovery, deduplication, permissions, failure recovery and manual add passed');
}
main().catch(error => {console.error(error); process.exitCode = 1;});
