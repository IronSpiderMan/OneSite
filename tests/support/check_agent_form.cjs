// node tests/support/check_agent_form.cjs /path/to/frontend-with-node_modules
// Execute the actual InputCard with a small hook host; network validation is driven
// through RelationInput's public callback, without a backend or business writes.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const frontend = path.resolve(process.argv[2]);
const esbuild = require(path.join(frontend, 'node_modules/esbuild'));
const template = fs.readFileSync(path.join(__dirname, '../../src/onesite/templates/codegen/agent_page.tsx.j2'), 'utf8');
const source = template.slice(template.indexOf('function InputCard('), template.indexOf('async function copyText('));
let state = [], cursor = 0, language = 'zh';
const dictionaries = {
  zh: {'models.device.name':'设备','models.device.fields.device_model_id':'设备模型','agent.form_title_create':'创建{{model}}','agent.form_invalid':'请检查 {{field}} 的填写内容。'},
  en: {'models.device.name':'Device','models.device.fields.device_model_id':'Device model','agent.form_title_create':'Create {{model}}','agent.form_invalid':'Check {{field}}.'},
};
const t = (key, options = {}) => (dictionaries[language][key] || options.defaultValue || key).replace(/\{\{(\w+)\}\}/g, (_, k) => options[k]);
const React = {createElement: (type, props, ...children) => ({type, props: {...props, children}})};
const useState = initial => {
 const index = cursor++;
 if (!(index in state)) state[index] = typeof initial === 'function' ? initial() : initial;
 return [state[index], next => { state[index] = typeof next === 'function' ? next(state[index]) : next; }];
};
function RelationInput() {}
const js = esbuild.transformSync(source, {loader:'tsx', jsx:'transform'}).code;
const InputCard = new Function('React','useState','useTranslation','RelationInput','formModelLabels','getErrorMessage', js + '\nreturn InputCard;')(
 React,useState,()=>({t}),RelationInput,{Device:{label_key:'models.device.name',field_labels:{device_model_id:'models.device.fields.device_model_id'}}},e=>String(e));
const value = {name:'Device_create',title:'Create a device',status:'pending',arguments:{body:{}},schema:{properties:{device_model_id:{type:'integer',title:'Device Model Id'}},required:['device_model_id']},initial:{device_model_id:1},ui:{fields:{device_model_id:{path:'/device_models',label_field:'name'}}}};
const submitted = [];
const render = () => {cursor = 0; return InputCard({value,disabled:false,onAnswer:async(action,values)=>submitted.push({action,values})});};
function nodes(tree) { if (!tree || typeof tree !== 'object') return []; if (Array.isArray(tree)) return tree.flatMap(nodes); return [tree,...nodes(tree.props.children)]; }
const relation = tree => nodes(tree).find(node=>node.type===RelationInput);
const submit = async tree => {nodes(tree).find(node=>node.type==='form').props.onSubmit({preventDefault(){}}); await Promise.resolve(); await Promise.resolve();};
(async()=>{
 let tree=render();
 assert.equal(tree.props['aria-label'],'创建设备');
 assert.match(JSON.stringify(tree),/设备模型/);
 relation(tree).props.onValidity(true); tree=render();
 relation(tree).props.onChange('1'); tree=render(); // Re-select the already verified ID.
 await submit(tree);
 assert.deepEqual(submitted,[{action:'submit',values:{device_model_id:1}}]);
 tree=render(); relation(tree).props.onChange('2'); tree=render();
 await submit(tree); assert.equal(submitted.length,1); // New ID still requires validation.
 tree=render(); assert.match(JSON.stringify(tree),/请检查 设备模型 的填写内容。/);
 relation(tree).props.onValidity(true); tree=render(); await submit(tree);
 assert.equal(submitted[1].values.device_model_id,2);
 language='en'; tree=render(); assert.equal(tree.props['aria-label'],'Create Device');
 assert.match(JSON.stringify(tree),/Device model/);
 console.log('Passed: same-ID re-selection, changed-ID validation, typed submission, Chinese/English titles and errors.');
})().catch(e=>{console.error(e);process.exitCode=1;});
