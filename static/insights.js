/* Independent visualizations and the editable war-detail workspace. */
function kdrTimeline(items, label='K/D across recorded wars') {
 if(!items.length)return empty('No recorded wars yet.');
 const finite=items.map(item=>item.deaths?item.kills/item.deaths:0),maximum=Math.max(1,...finite);
 const value=item=>item.deaths?item.kills/item.deaths:item.kills?maximum:0;
 const point=(item,index)=>[30+index*520/Math.max(items.length-1,1),150-value(item)/maximum*120];
 return `<svg class="chart" viewBox="0 0 580 180" role="img" aria-label="${esc(label)}"><polyline points="${items.map((item,index)=>point(item,index).join(',')).join(' ')}" fill="none" stroke="#78e1c4" stroke-width="3"/>${items.map((item,index)=>{const [x,y]=point(item,index);return `<circle cx="${x}" cy="${y}" r="5" fill="#e2bd78"><title>${esc(item.date||item.at)}: ${item.deaths?ratio(item.kills/item.deaths):item.kills?'∞ (zero deaths)':'0.00'} K/D</title></circle>`;}).join('')}<text x="30" y="174">Zero-death wins appear at the chart ceiling; hover for exact values.</text></svg>`;
}
function classBubbles() {
 const classes=Object.entries(state.analytics.composition),nodes=classes.map(([name,count],index)=>({name,count,x:90+(index%5)*100,y:70+Math.floor(index/5)*100,r:22+Math.sqrt(count)*7}));
 const height=Math.max(220,Math.ceil(nodes.length/5)*110);
 return {nodes,height,html:`<svg id="class-bubbles" class="chart" viewBox="0 0 580 ${height}" role="img" aria-label="Interactive class composition bubbles">${nodes.map((node,index)=>{const specs={};records('member').filter(m=>m.active&&m.class===node.name).forEach(m=>specs[m.spec]=(specs[m.spec]||0)+1);return `<g data-bubble="${index}" transform="translate(${node.x} ${node.y})"><circle r="${node.r}" fill="#244b48" stroke="#78e1c4"/><text text-anchor="middle" dy="-3">${esc(node.name)}</text><text text-anchor="middle" dy="15">${node.count}</text><title>${Object.entries(specs).map(([spec,count])=>esc(spec)+': '+count).join(' · ')}</title></g>`;}).join('')}</svg>`};
}
function animateBubbles(nodes,height) {
 const svg=$('#class-bubbles');if(!svg)return;let frame=0,dragging=null;
 const position=event=>{const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;return point.matrixTransform(svg.getScreenCTM().inverse());};
 svg.querySelectorAll('[data-bubble]').forEach(group=>{group.style.cursor='grab';group.onpointerdown=event=>{dragging=Number(group.dataset.bubble);svg.setPointerCapture(event.pointerId);};});
 svg.onpointermove=event=>{if(dragging===null)return;const p=position(event);nodes[dragging].x=p.x;nodes[dragging].y=p.y;frame=0;};
 svg.onpointerup=()=>{dragging=null;};
 function tick(){if(!svg.isConnected)return;
  for(let i=0;i<nodes.length;i++){const a=nodes[i];for(let j=i+1;j<nodes.length;j++){const b=nodes[j],dx=b.x-a.x,dy=b.y-a.y,distance=Math.hypot(dx,dy)||1,overlap=a.r+b.r+8-distance;if(overlap>0){const x=dx/distance*overlap*.3,y=dy/distance*overlap*.3;if(i!==dragging){a.x-=x;a.y-=y;}if(j!==dragging){b.x+=x;b.y+=y;}}}a.x=Math.max(a.r,Math.min(580-a.r,a.x));a.y=Math.max(a.r,Math.min(height-a.r,a.y));svg.querySelector(`[data-bubble="${i}"]`).setAttribute('transform',`translate(${a.x} ${a.y})`);}
  frame++;if(frame<90||dragging!==null)requestAnimationFrame(tick);else svg.onpointerdown=()=>{frame=0;requestAnimationFrame(tick);};
 }requestAnimationFrame(tick);
}
function rosterPriority() {
 const players=state.analytics.members.filter(m=>m.timeline.length).slice().sort((a,b)=>(b.kdr??Infinity)-(a.kdr??Infinity));
 const dates=[...new Set(players.flatMap(m=>m.timeline.map(w=>w.date)))].sort(),ceiling=Math.max(1,...players.flatMap(m=>m.timeline.map(w=>w.deaths?w.kills/w.deaths:0)));
 return `<article class="card section"><h2>Roster K/D trends</h2><svg class="chart" viewBox="0 0 580 180" aria-label="Roster priority trends" role="img">${players.map((member,index)=>`<polyline data-priority-line="${member.id}" points="${member.timeline.map(w=>`${30+dates.indexOf(w.date)*520/Math.max(1,dates.length-1)},${150-(w.deaths?w.kills/w.deaths:w.kills?ceiling:0)/ceiling*120}`).join(' ')}" fill="none" stroke="hsl(${index*67%360} 65% 65%)" stroke-width="2"><title>${esc(member.name)}</title></polyline>`).join('')}</svg><div class="pill-row">${players.map((member,index)=>`<label><input type="checkbox" checked data-priority-toggle="${member.id}"> ${esc(member.name)} · ${ratio(member.kdr)}</label>`).join('')}</div></article>`;
}
function renderInsights() {
 const section=document.createElement('section'),bubbles=classBubbles();section.innerHTML=`<div class="split section"><article class="card"><h2>Guild K/D timeline</h2>${kdrTimeline(state.analytics.timeline)}</article><article class="card"><h2>Class specializations</h2><p>Drag classes to rearrange; hover for specializations.</p>${bubbles.html}</article></div>${rosterPriority()}`;$('#panel').append(section);animateBubbles(bubbles.nodes,bubbles.height);
 section.querySelectorAll('[data-priority-toggle]').forEach(input=>input.onchange=()=>section.querySelector(`[data-priority-line="${input.dataset.priorityToggle}"]`).style.display=input.checked?'':'none');
}
function showWarDetails(war,order='kills') {
 const participants=war.participants.slice().sort((a,b)=>order==='name'?name(a.member).localeCompare(name(b.member)):order==='kdr'?(b.deaths?b.kills/b.deaths:b.kills?Infinity:0)-(a.deaths?a.kills/a.deaths:a.kills?Infinity:0):b[order]-a[order]);
 const total=participants.reduce((sum,p)=>({kills:sum.kills+p.kills,deaths:sum.deaths+p.deaths}),{kills:0,deaths:0}),classes={};participants.forEach(p=>classes[p.class]=(classes[p.class]||0)+1);
 const best=metric=>participants.slice().sort((a,b)=>metric(b)-metric(a))[0],awards=[['Most kills',best(p=>p.kills)],['Best K/D',best(p=>p.deaths?p.kills/p.deaths:p.kills?Infinity:0)],['Most deaths',best(p=>p.deaths)]];
 const editable=state.role!=='member';
 const workflow=warWorkflow(war);showContent(`${war.date} · ${war.type}`,`<p>${esc(war.result)} · ${war.capped?esc(war.cap||'Capped'):'Uncapped'} · ${participants.length} players · ${total.kills} kills · ${total.deaths} deaths</p>${war.location||war.opponents?`<p>${war.location?`<strong>${esc(war.location)}</strong>`:''}${war.opponents?` · vs ${esc(war.opponents)}`:''}</p>`:''}<div class="notice"><strong>War workflow</strong><p>${esc(workflow.label)}</p></div><div class="pill-row">${awards.map(([label,p])=>`<span class="badge">${label}: ${esc(p?name(p.member):'—')}</span>`).join('')}</div><p>${Object.entries(classes).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([label,count])=>esc(label)+': '+count).join(' · ')}</p><label for="war-detail-sort">Sort players</label><select id="war-detail-sort">${['name','kills','deaths','kdr'].map(value=>`<option ${value===order?'selected':''}>${value}</option>`).join('')}</select>${table(['Member','Class','Kills','Deaths','K/D','Excluded','Actions'],participants.map(p=>`<tr data-detail-member="${p.member}"><td>${esc(name(p.member))}</td><td>${editable?`<input data-detail-class aria-label="${esc(name(p.member))} class" value="${esc(p.class)}">`:esc(p.class)}</td><td>${editable?`<input data-detail-kills aria-label="${esc(name(p.member))} kills" type="number" min="0" value="${p.kills}">`:p.kills}</td><td>${editable?`<input data-detail-deaths aria-label="${esc(name(p.member))} deaths" type="number" min="0" value="${p.deaths}">`:p.deaths}</td><td>${ratio(p.deaths?p.kills/p.deaths:p.kills?null:0)}</td><td><input data-detail-excluded type="checkbox" aria-label="Exclude ${esc(name(p.member))}" ${p.excluded?'checked':''} ${editable?'':'disabled'}></td><td data-detail-actions="${p.member}"></td></tr>`))}<p>${esc(war.note||'')}</p>`);
 $('#war-detail-sort').onchange=event=>showWarDetails(war,event.target.value);
 if(editable)document.querySelectorAll('[data-detail-actions]').forEach(cell=>{
  const row=cell.closest('tr'),member=cell.dataset.detailActions;
  async function update(remove){try{let updated=war.participants.map(p=>p.member===member?{...p,kills:Number(row.querySelector('[data-detail-kills]').value),deaths:Number(row.querySelector('[data-detail-deaths]').value),class:row.querySelector('[data-detail-class]').value,excluded:row.querySelector('[data-detail-excluded]').checked}:p);if(remove)updated=updated.filter(p=>p.member!==member);const result=await call('wars','save',{id:war.id,participants:updated});showWarDetails(result,order);}catch(error){$('#form-error').textContent=error.message;}}
  cell.append(button('Save row',()=>update(false)),button('Remove',()=>update(true)));
 });
}

// Every debrief view uses the same replay prefix and guild scope as the feed.
function renderLiveBreakdown(events, guild) {
 const groups=new Map(),players=new Map(),classes=new Map(),minutes=new Map();
 let kills=0,deaths=0;
 function add(map,key,label,field){if(!map.has(key))map.set(key,{label,kills:0,deaths:0});map.get(key)[field]++;}
 for(const event of events){
  const field=event.kind==='kill'?'kills':'deaths';if(field==='kills')kills++;else deaths++;
  const character=event.kind==='kill'?event.target:event.player;
  const player=familyNames&&event.family?event.family:character;
  add(groups,event.guild,event.guild,field);
  add(players,JSON.stringify([event.guild,player]),`${player} · ${event.guild}`,field);
  add(classes,event.class,event.class,field);
  add(minutes,event.at.slice(0,16),event.at.slice(0,16),field);
 }
 const breakdown=(title,values)=>`<article class="card section"><h3>${title}</h3>${values.size?table(['Opponent','Our kills','Our deaths','Our K/D'],[...values.values()].sort((a,b)=>b.kills-a.kills||a.label.localeCompare(b.label)).map(v=>`<tr><td>${esc(v.label)}</td><td>${v.kills}</td><td>${v.deaths}</td><td>${ratio(v.deaths?v.kills/v.deaths:v.kills?null:0)}</td></tr>`)):empty('No opponents in this replay scope.')}</article>`;
 const timeline=[...minutes.values()].sort((a,b)=>a.label.localeCompare(b.label)).map(v=>({at:v.label,kills:v.kills,deaths:v.deaths}));
 $('#live-breakdown').innerHTML=`<article class="card section"><h3>${esc(guild||'All enemy guilds')}</h3><p id="live-totals">${kills} kills · ${deaths} deaths · ${ratio(deaths?kills/deaths:kills?null:0)} K/D</p><p>All statistics follow the replay position and selected guild. Kills and deaths are from our guild’s perspective.</p>${timeline.length?chart(timeline,'Kills in live replay'):empty('No timeline events yet.')}</article>${breakdown('Opposing guilds',groups)}<div class="split">${breakdown(familyNames?'Enemy families':'Enemy characters',players)}${breakdown('Enemy classes',classes)}</div>`;
}
