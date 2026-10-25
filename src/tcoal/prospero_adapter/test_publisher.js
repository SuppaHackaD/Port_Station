'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'../../..'),sdk=require(path.join(root,'sdk/prospero-achievements/bridge/prospero_file_bridge.js'));
// Called by the host integration suite; all file operations use its private fixture.
const folder=process.argv[2],ids=process.argv.slice(3),calls=[];
const source=fs.readFileSync(process.env.PA_TCOAL_HOOK_SOURCE||path.join(__dirname,'tcoal_hook.js'),'utf8').replace('__TCOAL_IDS__',JSON.stringify(['EP1_CLEAR','EP2_CLEAR','WARDEN_WINS']));
const steam={awardAchievement:function(id,extra){calls.push([this===steam,id,extra]);return 'original-result';}};
const context={Steam:steam,Utils:{isOptionValid:()=>false},setTimeout:()=>{},ProsperoFileBridge:{create(options){options.contextFile=path.join(folder,'tcoal-context-v1.txt');return sdk.create(options);}}};context.window=context;
vm.runInNewContext(source,context,{timeout:1000});
for(const id of ids){assert.strictEqual(context.Steam.awardAchievement(id,42),'original-result');}
assert.strictEqual(calls.length,ids.length);assert(calls.every(x=>x[0]&&x[2]===42));
const before=fs.readFileSync(path.join(folder,'tcoal-'+context.TCOALProspero.userId+'.tsv'),'utf8');context.Utils.isOptionValid=()=>true;context.Steam.awardAchievement('EP2_CLEAR',42);
assert.strictEqual(fs.readFileSync(path.join(folder,'tcoal-'+context.TCOALProspero.userId+'.tsv'),'utf8'),before);
// A transport failure must never change the game's own return or exception behavior.
context.Utils.isOptionValid=()=>false;
console.log(JSON.stringify({calls:calls.length,user:context.TCOALProspero.userId,hook:context.TCOALProspero.installed,testModePreserved:true}));
