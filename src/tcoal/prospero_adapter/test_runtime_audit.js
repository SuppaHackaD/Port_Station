'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const input = fs.readFileSync(path.join(__dirname,'runtime_audit.js'),'utf8');
let methodsCalled=0,gettersCalled=0,writes=[],timers=[];
const doNotCall=function(){methodsCalled++;throw new Error('observer called game API');};
const steam={activateAchievement:doNotCall,init:doNotCall};
Object.defineProperty(steam,'achievementGetter',{get(){gettersCalled++;throw new Error('getter invoked');}});
const req=name=>{assert.strictEqual(name,'fs');return {appendFileSync(file,text,encoding){assert.strictEqual(file,'C:/TCOAL-prospero-audit-v1.jsonl');assert.strictEqual(encoding,'utf8');writes.push(JSON.parse(text));}};};
req.cache={'C:/Game/www/greenworks/greenworks.js':{exports:steam}};
const context={require:req,setTimeout(f,ms){assert(ms===3000||ms===5000);timers.push(f);},DataManager:{autoSave:doNotCall,loadDatabase:doNotCall},ConfigManager:{save:doNotCall,language:'pt-BR'},Window_Options:function(){},Game_Interpreter:function(){},$gameSystem:{achievementMask:0},SceneManager:{_scene:{constructor:{name:'Scene_Title'}}},document:{scripts:[{src:'file:///C:/Game/www/js/main.js'}]},SteamManager:steam};
context.Window_Options.prototype.addGeneralOptions=doNotCall;context.Game_Interpreter.prototype.pluginCommand=doNotCall;context.window=context;
vm.runInNewContext(input,context,{timeout:1000});
while(timers.length){assert(writes.length<12);timers.shift()();}
assert.strictEqual(writes.length,12);assert.strictEqual(methodsCalled,0);assert.strictEqual(gettersCalled,0);
assert.strictEqual(writes[0].scene,'Scene_Title');assert(writes[0].candidates.includes('SteamManager'));
assert(writes[0].methods['DataManager.autoSave'].available);assert(writes[0].module_exports['C:/Game/www/greenworks/greenworks.js'].keys.includes('activateAchievement'));
assert(writes.every(x=>x.diagnostic==='tcoal-prospero-readonly-v1'));
console.log('Passive observer: 12 bounded records, game methods/getters untouched, fs log only.');
