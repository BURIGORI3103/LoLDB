// 生成されたアプリの実際の関数をDOMの最小代替上で実行する。
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes = new Map();
class Element {
  constructor(id='') { this.id=id; this.style={}; this.value=''; this.textContent=''; this.innerHTML=''; this.children=[]; this.isConnected=true; this.attrs={}; this.classes=new Set(); this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),contains:x=>this.classes.has(x),toggle:()=>{}}; }
  appendChild(x){this.children.push(x);} append(...x){this.children.push(...x);} replaceChildren(){this.children=[];}
  querySelector(){return new Element();} querySelectorAll(){return [];} setAttribute(k,v){this.attrs[k]=v;} getAttribute(k){return this.attrs[k];}
  addEventListener(){} focus(){document.activeElement=this;} getClientRects(){return [1];}
}
const node=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
const document={getElementById:node,querySelectorAll:()=>[],createElement:()=>new Element(),body:new Element('body'),activeElement:new Element('trigger')};
const events={}; let entries=[null],index=0;
const history={state:null,replaceState(s){this.state=s;entries[index]=s;},pushState(s){entries=entries.slice(0,index+1);entries.push(s);index++;this.state=s;},back(){if(index){this.state=entries[--index];events.popstate({state:this.state});}},forward(){if(index+1<entries.length){this.state=entries[++index];events.popstate({state:this.state});}}};
const timers=[];
const context={document,history,URL,console,navigator:{onLine:false},queueMicrotask:()=>{},setTimeout:f=>timers.push(f),Image:class{},localStorage:{getItem:()=>null,setItem:()=>{}},window:{addEventListener:(k,f)=>events[k]=f,scrollTo:()=>{}}};
vm.createContext(context);vm.runInContext(source,context,{timeout:5000});
const run=code=>vm.runInContext(code,context);
run('currentAttackFilter="HYBRID"; renderList()');
assert.match(node('countStatus').textContent,/表示中: 5 体/);
for(const query of ['エイトロックス','えいとろっくす','アトロックス','Aatrox','ジャーヴァンIV']){
  node('pickSearch').value=query;run('renderPickGuide()');assert.equal(node('pickCount').textContent,'1対面を表示',query);
}
run('openDetail("Garen"); openItemDetail("3070"); openItemDetail("3003")');
assert.equal(history.state.stack.at(-1).itemId,'3003');history.back();assert.equal(node('itemDetailName').textContent,'女神の涙');
history.back();assert(node('detailModal').classList.contains('open'));assert(!node('itemDetailModal').classList.contains('open'));
history.back();assert.equal(document.body.style.overflow,'');history.forward();assert.equal(document.body.style.overflow,'hidden');
run('openDetail("Cassiopeia")');assert.match(node('modalBody').innerHTML,/パッシブにより購入不可/);assert(!node('modalBody').innerHTML.includes('プレート スチールキャップ'));
run(`const attack='<img src=x onerror="globalThis.pwned=1">';
 CHAMPIONS.Garen.name=attack; CHAMPIONS.Garen.overview={summary:attack};
 const rd=getRoleData(CHAMPIONS.Garen,'TOP'); Object.assign(rd,{role_note:attack,skill_order:attack,gameplay_notes:{laning:attack,teamfight:attack},combos:[{name:attack,recipe:attack,desc:attack}],spell_sets:[{name:attack,spells:[attack]}]});
 CHAMPIONS.Garen.role_data.TOP=rd; rd.build_patterns[0].desc=attack; rd.build_patterns[0].name=attack;
 CHAMPIONS.Garen.spells[0].description=attack; openDetail('Garen');`);
assert(!node('modalBody').innerHTML.includes('<img src=x'));assert(node('modalBody').innerHTML.includes('&lt;img src=x'));
run('ITEMS["3070"].name=attack; ITEMS["3070"].stats_list=[attack]; openItemDetail("3070")');
assert(!node('itemDetailStatsText').innerHTML.includes('<img src=x'));
assert.equal(run('safeExternalUrl("javascript:alert(1)")'),'');
assert.equal(run('safeImageUrl("https://evil.example/a.png")'),'icon.png');
const before=timers.length;run('navigator.onLine=true; navigator.serviceWorker={}; navigator.connection={saveData:true}; prewarmChampionImages()');assert.equal(timers.length,before);
run('navigator.connection={effectiveType:"2g"}; prewarmChampionImages()');assert.equal(timers.length,before);
console.log('UI検証: 複合フィルター、公式名・通称・かな検索、履歴の戻る/進む、靴非表示、描画境界、先読み制限 OK');
