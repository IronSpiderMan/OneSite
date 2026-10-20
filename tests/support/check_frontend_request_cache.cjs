const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const ts = require(process.argv[2]);
const dir = process.argv[3];
const clone = value => JSON.parse(JSON.stringify(value));
const deferred = () => {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
};
function setup(variant = 'normal') {
    const compiled = ts.transpileModule(fs.readFileSync(path.join(dir, `${variant}.ts`), 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
        reportDiagnostics: true,
    });
    assert.equal(compiled.diagnostics.length, 0);
    let now = 100_000;
    let revision = 0;
    const storage = new Map([['token', 'account-a'], ['user_role', 'admin']]);
    const calls = { list: 0, detail: 0, update: 0, create: 0, delete: 0, bulk: 0 };
    const records = Array.from({length: 60}, (_, i) => ({ id: i + 1, name: `item-${i + 1}`, rank: i + 1, owner_id: 1, enabled: false }));
    const services = {
        getRequestItems: async (page, size, filters) => {
            calls.list++;
            return { items: clone(records.slice((page - 1) * size, page * size)), total: records.length, page, size };
        },
        getRequestItem: async id => { calls.detail++; return clone(records.find(r => r.id === id)); },
        updateRequestItem: async (id, values) => {
            calls.update++; revision++;
            const row = records.find(r => r.id === id);
            Object.assign(row, values);
            return clone(row);
        },
        createRequestItem: async value => { calls.create++; revision++; const row = {id: 61, ...value}; records.push(row); return clone(row); },
        deleteRequestItem: async id => { calls.delete++; revision++; records.splice(records.findIndex(r => r.id === id), 1); return {deleted: id}; },
        bulkDeleteRequestItem: async ids => { calls.bulk++; revision++; return {deleted: ids.length}; },
    };
    const exports = {};
    vm.runInNewContext(compiled.outputText, {
        exports, Date: { now: () => now }, console: {error() {}},
        localStorage: { getItem: key => storage.get(key) ?? null },
        require: name => name === '../utils/query-cache' ? {getDataRevision: () => revision} : name === 'zustand' ? {create: init => {
            let state;
            const get = () => state;
            const set = next => { state = {...state, ...(typeof next === 'function' ? next(state) : next)}; };
            state = init(set, get);
            return {getState: get};
        }} : services,
    });
    return { store: exports.useRequestItemStore, calls, services, records, storage, externalWrite: () => { revision++; }, advance: ms => {now += ms;} };
}
function checkTypes() {
    const typed = path.join(dir, 'typed');
    fs.mkdirSync(path.join(typed, 'stores'), {recursive: true});
    fs.mkdirSync(path.join(typed, 'services'), {recursive: true});
    fs.mkdirSync(path.join(typed, 'utils'), {recursive: true});
    fs.writeFileSync(path.join(typed, 'zustand.d.ts'), `declare module 'zustand' {
        export function create<T>(init: (set: (value: Partial<T>) => void, get: () => T) => T): {getState: () => T};
    }`);
    fs.writeFileSync(path.join(typed, 'services/request_item.ts'), `
        export interface RequestItem {id: number; name: string; enabled: boolean; rank: number}
        export declare function getRequestItems(page: number, size: number, filters?: Record<string, any>): Promise<{items: RequestItem[]; total: number; page: number; size: number}>;
        export declare function getRequestItem(id: number): Promise<RequestItem>;
        export declare function createRequestItem(data: any): Promise<RequestItem>;
        export declare function updateRequestItem(id: number, data: any): Promise<RequestItem>;
        export declare function deleteRequestItem(id: number): Promise<{deleted: number}>;
        export declare function bulkDeleteRequestItem(ids: number[]): Promise<{deleted: number}>;
    `);
    fs.writeFileSync(path.join(typed, 'utils/query-cache.ts'), 'export declare function getDataRevision(): number;');
    const files = ['normal', 'resolver', 'tree', 'ordered', 'hook', 'owner'].map(variant => {
        const target = path.join(typed, 'stores', `${variant}.ts`);
        fs.copyFileSync(path.join(dir, `${variant}.ts`), target);
        return target;
    });
    files.push(path.join(typed, 'zustand.d.ts'));
    const program = ts.createProgram(files, {strict: true, noEmit: true, target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS});
    const diagnostics = ts.getPreEmitDiagnostics(program);
    assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
        getCanonicalFileName: f => f, getCurrentDirectory: () => dir, getNewLine: () => '\n',
    }));
}
async function main() {
    checkTypes();
    // Detail round-trip preserves pagination, raw form values and fresh empty/nonempty pages.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({});
        await s().fetchData(3, 10);
        await s().fetchItem(21);
        const before = x.calls.list;
        await s().ensureList({});
        assert.equal(x.calls.list, before);
        assert.equal(s().page, 3);
        assert.equal(s().size, 10);
        await s().updateItem(21, {name: 'saved'}, {refreshList: false});
        assert.equal(x.calls.update, 1);
        assert.equal(x.calls.detail, 1);
        assert.equal(x.calls.list, before);
        assert.equal(s().data[0].name, 'saved');
        assert.equal(s().currentItem.name, 'saved');
        await s().ensureList({});
        assert.equal(x.calls.list, before);
        await s().runAction(() => x.services.updateRequestItem(21, {enabled: true}));
        assert.equal(s().data[0].enabled, true);
        assert.equal(x.calls.list, before);
        x.advance(30_001);
        await s().ensureList({});
        assert.equal(x.calls.list, before + 1);
        await s().refreshData();
        assert.equal(x.calls.list, before + 2, 'explicit refresh bypasses freshness');
    }
    // Create page defers refreshing until the list is actually shown.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({});
        await s().createItem({name: 'new'}, {refreshList: false});
        assert.equal(x.calls.list, 1);
        await s().ensureList({});
        await s().ensureList({});
        assert.equal(x.calls.list, 2);
        await s().deleteItem(1);
        assert.equal(x.calls.list, 3);
        await s().bulkDeleteItem([2]);
        assert.equal(x.calls.list, 4);
    }
    // Filtered lists and function actions are invalidated; hidden lists refresh on return.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({parent_id: 7});
        s().setListSearchValues({name: 'item', enabled: 'false'});
        await s().fetchData(2, 10, {parent_id: 7, enabled: false});
        await s().updateItem(11, {enabled: true}, {refreshList: false});
        assert.equal(x.calls.list, 2);
        await s().ensureList({parent_id: 7});
        assert.equal(x.calls.list, 3);
        assert.equal(s().page, 2);
        assert.equal(s().filters.enabled, false);
        assert.equal(s().listSearchValues.enabled, 'false');
        await s().ensureList({parent_id: 8});
        assert.equal(x.calls.list, 4);
        assert.equal(s().page, 1);
        assert.equal(Object.keys(s().listSearchValues).length, 0);
        await s().runAction(() => x.services.updateRequestItem(1, {enabled: true}), {invalidateList: true});
        assert.equal(x.calls.list, 5);
    }
    // Default ordering and explicit ordering are revalidated only when their field changes.
    for (const variant of ['normal', 'ordered']) {
        const x = setup(variant), s = x.store.getState;
        await s().ensureList({});
        if (variant === 'normal') await s().setSorting('rank', 'asc');
        const before = x.calls.list;
        await s().updateItem(1, {name: 'safe'});
        assert.equal(x.calls.list, before);
        await s().updateItem(1, {rank: 100});
        assert.equal(x.calls.list, before + 1);
    }
    // A changed owner changes the server's implicit visibility filter.
    {
        const x = setup('owner'), s = x.store.getState;
        await s().ensureList({});
        await s().updateItem(1, {name: 'same owner'});
        assert.equal(x.calls.list, 1);
        await s().updateItem(1, {owner_id: 2});
        assert.equal(x.calls.list, 2);
    }
    // Trees never request ordinary pagination after their mutations.
    {
        const x = setup('tree'), s = x.store.getState;
        await s().updateItem(1, {name: 'tree'});
        await s().createItem({name: 'new'});
        await s().deleteItem(1);
        await s().bulkDeleteItem([2]);
        assert.equal(x.calls.list, 0);
    }
    // Context-sensitive read resolvers retain the detail read; update hooks invalidate lists.
    {
        const x = setup('resolver'), s = x.store.getState;
        await s().ensureList({});
        await s().fetchItem(1);
        x.services.getRequestItem = async id => {x.calls.detail++; return {id, name: 'detail projection'};};
        await s().updateItem(1, {name: 'write projection'}, {refreshList: false});
        assert.equal(s().currentItem.name, 'detail projection');
        assert.equal(s().data[0].name, 'item-1');
        assert.equal(x.calls.detail, 2);
        await s().ensureList({});
        assert.equal(x.calls.list, 2);
        const y = setup('hook');
        await y.store.getState().ensureList({});
        await y.store.getState().updateItem(1, {name: 'hook'});
        assert.equal(y.calls.list, 2);
    }
    // Coalesce mount/refresh requests; slow previous pages must not overwrite the selected page.
    {
        const x = setup(), s = x.store.getState;
        const pending = [];
        x.services.getRequestItems = (page, size) => {x.calls.list++; const d = deferred(); pending.push({d, page, size}); return d.promise;};
        const a = s().ensureList({});
        const b = s().ensureList({});
        const c = s().refreshData();
        assert.equal(x.calls.list, 1);
        pending[0].d.resolve({items: [{id: 1}], total: 60, page: 1, size: 20});
        await Promise.all([a, b, c]);
        const old = s().fetchData(2, 20);
        const latest = s().fetchData(3, 20);
        pending[2].d.resolve({items: [{id: 41}], total: 60, page: 3, size: 20});
        await latest;
        pending[1].d.resolve({items: [{id: 21}], total: 60, page: 2, size: 20});
        await old;
        assert.equal(s().page, 3);
        assert.equal(s().data[0].id, 41);
        assert.equal(s().loading, false);
    }
    // A pre-mutation list/detail response cannot undo a successful write response.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({});
        const list = deferred(), detail = deferred();
        x.services.getRequestItems = () => list.promise;
        x.services.getRequestItem = () => detail.promise;
        const oldList = s().refreshData();
        const oldItem = s().fetchItem(1);
        const sameItem = s().fetchItem(1);
        assert.equal(oldItem, sameItem);
        await s().updateItem(1, {name: 'new'}, {refreshList: false});
        list.resolve({items: [{id: 1, name: 'old'}], total: 1, page: 1, size: 20});
        detail.resolve({id: 1, name: 'old'});
        await Promise.all([oldList, oldItem]);
        assert.equal(s().currentItem.name, 'new');
        assert.equal(s().data[0].name, 'new');
        assert.equal(s().loading, false);
    }
    // Authentication identity changes clear cached data and reject old responses.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({});
        await s().fetchItem(1);
        const action = deferred();
        const running = s().runAction(() => action.promise);
        x.storage.set('token', 'account-b');
        assert.equal(s().canRestoreList({}), false);
        action.resolve({id: 1, name: 'account-a secret'});
        await running;
        assert.equal(s().currentItem, null);
        assert.equal(s().data.length, 0);
        await s().ensureList({});
        assert.equal(x.calls.list, 2);
    }
    // Writes from another model/inline relationship invalidate an otherwise fresh page.
    {
        const x = setup(), s = x.store.getState;
        await s().ensureList({});
        x.externalWrite();
        await s().ensureList({});
        assert.equal(x.calls.list, 2);
        x.externalWrite();
        await s().updateItem(1, {name: 'own write'});
        assert.equal(x.calls.list, 3, 'own write must not hide an unrelated earlier mutation');
    }
    // Failed requests are never cached as fresh, including empty query results.
    {
        const x = setup(), s = x.store.getState;
        x.services.getRequestItems = async () => {x.calls.list++; throw new Error('offline');};
        await s().ensureList({});
        await s().ensureList({});
        assert.equal(x.calls.list, 2);
        x.services.getRequestItems = async () => {x.calls.list++; return {items: [], total: 0, page: 1, size: 20};};
        await s().ensureList({});
        await s().ensureList({});
        assert.equal(x.calls.list, 3);
    }
    console.log('Generated store request lifecycle checks passed');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
