// 実際の生成SWで、古い配信内容によるキャッシュ汚染とオフライン復帰を再現する。
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const sw=fs.readFileSync('sw.js','utf8');
const html=fs.readFileSync('index.html','utf8').replace(/\r\n/g,'\n');
const base='https://example.test/LoLDB/';
const key=sw.match(/const CORE_CACHE = '([^']+)'/)[1];
function harness(body=html){
 const stores=new Map(),handlers={};let network=body,skipped=false;
 const absolute=value=>new URL(typeof value==='string'?value:value.url,base).href;
 const fetch=async request=>{if(network===null)throw Error('ネットワーク切断');return new Response(network,{status:200,headers:{'Content-Type':'text/html'}});};
 const caches={async open(name){if(!stores.has(name))stores.set(name,new Map());const map=stores.get(name);return {async put(r,v){map.set(absolute(r),v.clone());},async match(r){return map.get(absolute(r))?.clone();},async addAll(values){for(const value of values)this.put(value,await fetch(value));}};},async keys(){return [...stores.keys()];},async delete(name){return stores.delete(name);},async match(request){for(const name of stores.keys()){const value=await(await this.open(name)).match(request);if(value)return value;}}};
 const self={registration:{scope:base},location:{href:base+'sw.js'},clients:{async claim(){}},async skipWaiting(){skipped=true;},addEventListener:(event,callback)=>handlers[event]=callback};
 vm.runInNewContext(sw,{self,caches,fetch,URL,Request,Response,crypto:webcrypto,TextEncoder,console});
 return {caches,stores,setNetwork(value){network=value;},get skipped(){return skipped;},async install(){let promise;handlers.install({waitUntil:p=>promise=p});return promise;},async activate(){let promise;handlers.activate({waitUntil:p=>promise=p});await promise;},async navigate(){let promise;const waits=[];handlers.fetch({request:{url:base+'index.html',mode:'navigate',method:'GET'},respondWith:p=>promise=p,waitUntil:p=>waits.push(p)});const result=await promise;await Promise.all(waits);return result;}};
}
(async()=>{
 const stale=harness('<html>旧版の配信内容</html>');
 await assert.rejects(stale.install(),/HTML|ハッシュ/,'旧HTMLのプリキャッシュは失敗する必要がある');
 assert.equal(stale.skipped,false,'取得検証前に新SWへ切り替えない');
 const current=harness();await current.install();assert(current.skipped);
 const cache=await current.caches.open(key);assert.equal(await(await cache.match('./index.html')).text(),html);
 current.setNetwork('<html>一時的に古い配信内容</html>');await current.navigate();
 assert.equal(await(await cache.match('./index.html')).text(),html,'古いオンライン応答で検証済みキャッシュを上書きしない');
 current.setNetwork(null);assert.equal(await(await current.navigate()).text(),html,'切断後も検証済みのHTMLを返す');
 await current.caches.open('other-app-cache');await current.caches.open('loldb-core-old');await current.caches.open('loldb-images-v1');await current.activate();
 assert(current.stores.has('other-app-cache'));assert(current.stores.has('loldb-images-v1'));assert(!current.stores.has('loldb-core-old'));
 console.log('SW検証: 旧HTMLの拒否、切替順序、汚染防止、オフライン復帰、他アプリのキャッシュ保護 OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
