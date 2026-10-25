'use strict';
const $ = id => document.getElementById(id);
let games = [], states = {}, selected = null, filter = 'all', busy = false;
let user = localStorage.getItem('pa-user') || '';
function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function image(hash) { const n = el('img'); n.src = '/api/v1/assets/' + hash + '.png'; n.alt = ''; n.loading = 'lazy'; return n; }
async function api(path) { const r = await fetch('/api/v1/' + path, {cache:'no-store'}); const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Falha de consulta'); return data; }
function state(game) { return states[game.game_id] || {achievements:[]}; }
function count(game) { const s = state(game); return s.achievements.filter(a => a.unlocked).length; }
function bar(value) { const b = el('div','bar'), fill = el('span'); fill.style.width = Math.max(0,Math.min(100,value)) + '%'; b.append(fill); return b; }
function render() {
  $('games-count').textContent = games.length;
  $('unlocks-count').textContent = games.reduce((n,g) => n+count(g),0);
  $('complete-count').textContent = games.filter(g => count(g) === g.achievements.length).length;
  $('notice').textContent = !games.length ? 'Sua biblioteca ainda está vazia. Os jogos enviam seus catálogos ao payload pelo SDK; nenhum jogo precisa ser configurado manualmente aqui.' : !user ? 'Os catálogos estão disponíveis. O primeiro evento de um jogo criará seu perfil local.' : '';
  $('library').replaceChildren();
  for (const g of games) {
    const unlocked = count(g), total = g.achievements.length, card = el('button','game');
    const top = el('div','game-top'), info = el('div'); top.append(image(g.icon)); info.append(el('h3','',g.title),el('div','small',total+' conquistas')); top.append(info);
    const label = el('div','progress-label'); label.append(el('span','',unlocked+' de '+total+' obtidas'),el('span','',Math.round(unlocked/total*100)+'%'));
    card.append(top,label,bar(unlocked/total*100)); card.onclick=()=>{selected=g.game_id;filter='all';renderDetail();}; $('library').append(card);
  }
  if(selected) renderDetail();
}
function renderDetail() {
  const g = games.find(g => g.game_id === selected); if(!g) return;
  $('library').hidden=true; $('detail').hidden=false; $('detail-head').replaceChildren();
  const head=el('div','detail-head'), info=el('div'); head.append(image(g.icon));
  info.append(el('h2','',g.title),el('div','small',count(g)+' de '+g.achievements.length+' conquistas obtidas'),bar(count(g)/g.achievements.length*100));head.append(info);$('detail-head').append(head);
  $('achievements').replaceChildren();
  const byId = Object.fromEntries(state(g).achievements.map(a=>[a.id,a]));
  for(const a of g.achievements) {
    const s=byId[a.id]||{unlocked:false,progress:0,target:a.target};
    if(filter==='unlocked'&&!s.unlocked||filter==='locked'&&s.unlocked) continue;
    const card=el('article','achievement '+(s.unlocked?'unlocked':'locked')), info=el('div');
    if(a.icon) card.append(image(a.icon)); else card.append(el('div','symbol',a.completion?'✦':s.unlocked?'◆':'◇'));
    const hidden=a.hidden&&!s.unlocked;
    info.append(el('h3','',hidden?'Conquista secreta':a.title),el('p','',hidden?'Continue sua jornada para descobrir.':a.description));
    if(s.unlocked) { const t=el('time','',s.unlocked_at>0?new Date(s.unlocked_at*1000).toLocaleString('pt-BR'):'Obtida');info.append(t); }
    else if(a.target>1) info.append(el('div','small',s.progress+' / '+a.target),bar(s.progress/a.target*100));
    card.append(info);$('achievements').append(card);
  }
  if(!$('achievements').children.length) $('achievements').append(el('p','empty','Nenhuma conquista neste filtro.'));
  document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b.dataset.filter===filter));
}
async function refresh() {
  if(busy) return;busy=true;
  try {
    const [info,catalog,profiles]=await Promise.all([api('info'),api('games'),api('users')]);
    games=catalog.games.sort((a,b)=>a.title.localeCompare(b.title)); const users=profiles.users.sort();
    if(!users.includes(user)) user=users[0]||'';
    $('user').replaceChildren();
    if(!users.length) $('user').append(new Option('Nenhum perfil registrado',''));
    for(const id of users) $('user').append(new Option('Usuário '+id,id));$('user').value=user;
    states={};
    if(user) await Promise.all(games.map(async g=>{states[g.game_id]=await api('state/'+user+'/'+g.game_id);}));
    $('connection').textContent='Payload ativo';$('dot').className='online';
    $('service-info').textContent='v'+info.version+' · ativo há '+Math.floor(info.uptime_ms/60000)+' min';
    $('footer-info').textContent='Dados locais · API '+info.api_major;
    $('updated').textContent='Atualizado às '+new Date().toLocaleTimeString('pt-BR');
    render();
  } catch(e) { $('connection').textContent='Sem conexão';$('dot').className='';$('notice').textContent='Não foi possível consultar o payload: '+e.message; }
  finally {busy=false;}
}
$('user').onchange=()=>{user=$('user').value;localStorage.setItem('pa-user',user);refresh();};
$('back').onclick=()=>{selected=null;$('detail').hidden=true;$('library').hidden=false;};
document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;renderDetail();});
refresh();setInterval(refresh,4000);
