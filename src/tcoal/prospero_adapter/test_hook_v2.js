'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const sdk=require(path.resolve(__dirname,'../../../sdk/prospero-achievements/bridge/prospero_file_bridge.js'));
const folder=process.argv[2];fs.mkdirSync(folder,{recursive:true});fs.writeFileSync(path.join(folder,'tcoal-context-v1.txt'),'PA_FILE_CONTEXT_V1\ttcoal\t0000002a\n');
const source=fs.readFileSync(path.join(__dirname,'tcoal_hook_v2.js'),'utf8').replace('__TCOAL_IDS__','["WARDEN_WINS","EP1_CLEAR","EP2_CLEAR"]');
const timers=[],originalCalls=[];
const api={activateAchievement:function(id){originalCalls.push(['api',this===api,id]);return 71;}};
const steam={API:api,awardAchievement:function(id){originalCalls.push(['game',this===steam,id]);return this.API.activateAchievement(id);}};
const cached=steam.awardAchievement.bind(steam); // Cached before the game's property is wrapped.
const context={Steam:steam,Utils:{isOptionValid:()=>false},Window_ChoiceList:function(){},setTimeout(f){timers.push(f);},require(name){assert.strictEqual(name,'fs');return {appendFileSync(file,s,encoding){assert(file.endsWith('tcoal-bridge-v2-0000002a.jsonl'));fs.appendFileSync(path.join(folder,'diagnostics.jsonl'),s,encoding);}};},ProsperoFileBridge:{create(opts){opts.contextFile=path.join(folder,'tcoal-context-v1.txt');return sdk.create(opts);}}};
context.Window_ChoiceList.prototype.addCommand=function(name){return 'choice:'+name;};context.window=context;
vm.runInNewContext(source,context,{timeout:1000});
assert.strictEqual(cached('WARDEN_WINS'),71); // API route catches an existing cached game function.
assert.strictEqual(steam.awardAchievement('WARDEN_WINS'),71);
let text=fs.readFileSync(path.join(folder,'tcoal-0000002a.tsv'),'utf8');assert.strictEqual((text.match(/PA_FILE_UNLOCK_V1/g)||[]).length,1);
steam.awardAchievement=function(id){originalCalls.push(['replacement',this===steam,id]);return this.API.activateAchievement(id)+1;};
timers.shift()();assert.strictEqual(steam.awardAchievement('EP1_CLEAR'),72);
api.activateAchievement=function(id){originalCalls.push(['newApi',this===api,id]);return 90;};timers.shift()();assert.strictEqual(cached('EP2_CLEAR'),90);
const old=fs.readFileSync(path.join(folder,'tcoal-0000002a.tsv'),'utf8');context.Utils.isOptionValid=()=>true;steam.awardAchievement('WARDEN_WINS');assert.strictEqual(fs.readFileSync(path.join(folder,'tcoal-0000002a.tsv'),'utf8'),old);
context.Utils.isOptionValid=()=>false;steam.awardAchievement('UNKNOWN');assert.strictEqual(fs.readFileSync(path.join(folder,'tcoal-0000002a.tsv'),'utf8'),old);
const choice=new context.Window_ChoiceList();assert.strictEqual(choice.addCommand('(label)[Missing]'),'choice:(label)[Missing]');
const logs=fs.readFileSync(path.join(folder,'diagnostics.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
assert(logs.some(x=>x.event==='award.request'&&x.data.layer==='api'&&x.data.id==='WARDEN_WINS'&&x.data.published));
assert(logs.some(x=>x.event==='hook.ready'&&x.data.replaced));assert(logs.some(x=>x.event==='choice.unresolved'));assert(originalCalls.every(x=>x[1]));
assert.strictEqual((old.match(/PA_FILE_UNLOCK_V1/g)||[]).length,3);
console.log('V2 hook: cached aliases/API route, reattachment, deduplication, test mode, this/return and choice logging passed.');
