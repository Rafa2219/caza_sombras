
// Configuración del backend
const API_BASE_URL = window.location.origin;

// Elementos del DOM
const gameCanvas = document.getElementById('game');
const ctx = gameCanvas.getContext('2d');

// GAME CONFIG
const TILE = 32;
const MAP_W = 20, MAP_H = 11;
const PLAYER_SPEED = 2.2;
let foundCount = 0;
let gameTime = 0;
let gameTimer = null;
let gameCompleted = false;
let nearItem = null;

// Player state
const player = {
  x: TILE*2 + TILE/2, y: TILE*2 + TILE/2,
  vx:0, vy:0,
  dir: 'down',
  animFrame:0,
  animTick:0,
  moving:false
};

const pressedKeys = new Set();

// Game map (mantener tu código existente)
const map = [];
for(let y=0;y<MAP_H;y++){
  map[y] = [];
  for(let x=0;x<MAP_W;x++){
    if(y===0||y===MAP_H-1||x===0||x===MAP_W-1) map[y][x]=1;
    else map[y][x] = Math.random() < 0.05 ? 2 : (Math.random() < 0.12 ? 3 : (Math.random() < 0.02 ? 5 : 0));
  }
}

for(let i=0;i<14;i++){
  const tx = 2 + Math.floor(Math.random()*(MAP_W-4));
  const ty = 2 + Math.floor(Math.random()*(MAP_H-4));
  map[ty][tx] = 1;
}

// Hidden items
const items = [];
const ITEM_TYPES = [
  { name: 'regalo_rojo', color: '#ff4444', symbol: '🎁' },
  { name: 'regalo_verde', color: '#44ff44', symbol: '🎁' },
  { name: 'muñeco_nieve', color: '#ffffff', symbol: '⛄' }
];

for(let i=0;i<10;i++){
  let tries=0;
  while(tries<200){
    const rx = 1 + Math.floor(Math.random()*(MAP_W-2));
    const ry = 1 + Math.floor(Math.random()*(MAP_H-2));
    if((map[ry][rx]===3 || map[ry][rx]===1 || map[ry][rx]===2) && !items.find(it=>it.xTile===rx && it.yTile===ry)){
      const itemType = ITEM_TYPES[Math.floor(Math.random()*ITEM_TYPES.length)];
      items.push({
        xTile:rx, yTile:ry,
        type: itemType.name,
        color: itemType.color,
        symbol: itemType.symbol,
        found:false
      });
      break;
    }
    tries++;
  }
}
document.getElementById('total').textContent = items.length;

// ========== FUNCIONES DE API MEJORADAS ==========
async function submitScore(discordId, score) {
  try {
    console.log(`📤 Enviando puntuación: ${discordId} - ${score} segundos`);
    
    const response = await fetch('/score', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        discord_id: discordId,
        score: score
      })
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || `Error ${response.status}`);
    }

    if (data.status === 'success') {
      showMessage('¡Puntaje guardado exitosamente! 🎉', 'success');
      return true;
    } else {
      showMessage(data.message || 'Error al guardar puntaje', 'error');
      return false;
    }
  } catch (error) {
    console.error('❌ Error enviando puntuación:', error);
    showMessage(`Error: ${error.message}`, 'error');
    return false;
  }
}

async function loadLeaderboard() {
  try {
    console.log('📥 Cargando leaderboard...');
    const response = await fetch('/scores');
    
    if (!response.ok) {
      throw new Error(`Error HTTP ${response.status}: ${response.statusText}`);
    }
    
    const scores = await response.json();
    const leaderboardElement = document.getElementById('leaderboard');
    
    // Verificar si la respuesta es un array
    if (!Array.isArray(scores)) {
      console.warn('⚠️ La respuesta no es un array:', scores);
      leaderboardElement.innerHTML = '<div style="text-align:center; padding:20px;">Formato de datos inesperado</div>';
      return;
    }
    
    if (scores.length === 0) {
      leaderboardElement.innerHTML = '<div style="text-align:center; padding:20px;">No hay puntuaciones aún</div>';
      return;
    }
    
    let leaderboardHTML = '';
    scores.forEach((score, index) => {
      const date = score.date ? new Date(score.date).toLocaleDateString('es-ES') : 'Fecha desconocida';
      const discordId = score.discord_id || 'Anónimo';
      const scoreValue = score.score !== undefined ? score.score : 'N/A';
      
      leaderboardHTML += `
        <div class="leaderboard-item">
          <span>${index + 1}. ${discordId}</span>
          <span>${scoreValue} seg</span>
          <small>${date}</small>
        </div>
      `;
    });
    
    leaderboardElement.innerHTML = leaderboardHTML;
    console.log(`✅ Leaderboard cargado: ${scores.length} registros`);
    
  } catch (error) {
    console.error('❌ Error cargando leaderboard:', error);
    document.getElementById('leaderboard').innerHTML = 
      `<div style="text-align:center; padding:20px; color:#ff6b6b;">
        Error cargando ranking: ${error.message}
       </div>`;
  }
}

// ========== FUNCIONES DEL JUEGO (mantener tu código existente) ==========
function startGameTimer() {
  gameTime = 0;
  gameTimer = setInterval(() => {
    gameTime++;
    document.getElementById('timer').textContent = gameTime;
  }, 1000);
}

function stopGameTimer() {
  if (gameTimer) {
    clearInterval(gameTimer);
    gameTimer = null;
  }
}

function showMessage(text, type = 'info') {
  const messageElement = document.getElementById('message');
  messageElement.textContent = text;
  messageElement.style.color = type === 'error' ? '#ff6b6b' : 
                              type === 'success' ? '#51cf66' : '#ffd86b';
  
  setTimeout(() => {
    messageElement.textContent = '';
  }, 3000);
}

function showScoreModal() {
  document.getElementById('finalTime').textContent = gameTime;
  document.getElementById('scoreModal').style.display = 'flex';
  document.getElementById('discordId').value = '';
  document.getElementById('discordId').focus();
}

function showLeaderboard() {
  loadLeaderboard();
  document.getElementById('leaderboardModal').style.display = 'flex';
}

function checkNearbyItems() {
  const pTileX = Math.floor(player.x / TILE);
  const pTileY = Math.floor(player.y / TILE);
  
  nearItem = null;
  
  items.forEach(it => {
    if (!it.found) {
      const distance = Math.abs(it.xTile - pTileX) + Math.abs(it.yTile - pTileY);
      if (distance <= 1) {
        nearItem = it;
      }
    }
  });
  
  if (nearItem) {
    document.getElementById('message').textContent = 'Presiona E para recoger';
    document.getElementById('message').style.color = '#ffd86b';
  } else {
    document.getElementById('message').textContent = '';
  }
}

function collectItem() {
  if (nearItem && !nearItem.found) {
    nearItem.found = true;
    foundCount++;
    document.getElementById('found').textContent = foundCount;
    addInventoryItem(nearItem.type);
    
    nearItem = null;
    document.getElementById('message').textContent = '';
    
    if (foundCount === items.length && !gameCompleted) {
      gameCompleted = true;
      stopGameTimer();
      setTimeout(() => {
        showScoreModal();
      }, 1000);
    }
  }
}

// ========== EVENT LISTENERS ==========
document.getElementById('submitScore').addEventListener('click', async () => {
  const discordId = document.getElementById('discordId').value.trim();
  
  if (!discordId) {
    showMessage('Por favor ingresa tu ID de Discord', 'error');
    return;
  }
  
  const success = await submitScore(discordId, gameTime);
  if (success) {
    document.getElementById('scoreModal').style.display = 'none';
  }
});

document.getElementById('cancelScore').addEventListener('click', () => {
  document.getElementById('scoreModal').style.display = 'none';
});

document.getElementById('leaderboardBtn').addEventListener('click', showLeaderboard);
document.getElementById('closeLeaderboard').addEventListener('click', () => {
  document.getElementById('leaderboardModal').style.display = 'none';
});

document.getElementById('collectBtn').addEventListener('click', collectItem);

// Close modals cuando se hace click fuera
document.querySelectorAll('.modal').forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
});

// ========== RESTANTE DEL CÓDIGO DEL JUEGO (mantener igual) ==========
// [Aquí va todo el resto de tu código JavaScript existente para el juego:
// drawPlayer, drawTile, isPassable, input handling, game loop, etc.]
// ... (todo el código de dibujo y lógica del juego que ya tenías)

// Player drawing function
function drawPlayer(ctx,px,py){
  const f = player.animFrame;
  const body = '#ffdf80';
  const hat = '#c62828';
  const muff = '#ffffff';
  
  ctx.fillStyle = body;
  ctx.fillRect(px-8, py-12, 16, 20);
  
  ctx.fillStyle = (player.moving && f%2===0) ? '#874b2f' : '#6b3b21';
  ctx.fillRect(px-6, py+6, 6, 6);
  ctx.fillRect(px+0, py+6, 6, 6);
  
  ctx.fillStyle = '#ffd8b6';
  ctx.fillRect(px-7, py-20, 14, 12);
  
  ctx.fillStyle = hat;
  ctx.fillRect(px-10, py-26, 20, 6);
  
  ctx.fillStyle = muff;
  ctx.fillRect(px+6, py-28, 4, 4);
}

// Tile drawing function
function drawTile(ctx,tx,ty,tile){
  const px = tx*TILE, py = ty*TILE;
  switch(tile){
    case 0:
      ctx.fillStyle = '#1e6b3a';
      ctx.fillRect(px,py,TILE,TILE);
      if(Math.random()<0.03){ ctx.fillStyle='#e6f7ff'; ctx.fillRect(px+4,py+4,6,6); }
      break;
    case 1:
      ctx.fillStyle = '#4b2c12';
      ctx.fillRect(px+TILE*0.45,py+TILE*0.6,TILE*0.1,TILE*0.4);
      ctx.fillStyle = '#0d5b2e';
      ctx.beginPath();
      ctx.moveTo(px+TILE*0.5, py+4);
      ctx.lineTo(px+4, py+TILE*0.65);
      ctx.lineTo(px+TILE-4, py+TILE*0.65);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#ecf7ff';
      ctx.fillRect(px+6,py+6,6,2);
      break;
    case 2:
      ctx.fillStyle = '#6f6f6f';
      ctx.fillRect(px+6,py+10,TILE-12,TILE-8);
      break;
    case 3:
      ctx.fillStyle = '#0f5e2a';
      ctx.fillRect(px+4,py+8,TILE-8,TILE-6);
      ctx.fillStyle = '#ff293b';
      ctx.fillRect(px+8,py+12,2,2);
      break;
    case 4:
      ctx.fillStyle = '#dfefff';
      ctx.fillRect(px,py,TILE,TILE);
      break;
    case 5:
      ctx.fillStyle = '#073a6b';
      ctx.fillRect(px,py,TILE,TILE);
      break;
  }
}

function isPassable(tx,ty){
  if(tx<0||ty<0||tx>=MAP_W||ty>=MAP_H) return false;
  const t = map[ty][tx];
  return !(t===1 || t===2 || t===5);
}

// Input handling
window.addEventListener('keydown', (e) => {
  const k = e.key.toLowerCase();
  pressedKeys.add(k);
  
  if (k === 'e') {
    e.preventDefault();
    collectItem();
  }
  
  if(['arrowup','arrowdown','arrowleft','arrowright',' '].includes(k)) e.preventDefault();
});

window.addEventListener('keyup', (e) => {
  pressedKeys.delete(e.key.toLowerCase());
});

// Mobile D-Pad
document.getElementById('dpad').addEventListener('touchstart', (ev)=>{
  ev.preventDefault();
  const btn = ev.target.closest('button');
  if(!btn) return;
  handleDpad(btn.dataset.dir, true);
});

document.getElementById('dpad').addEventListener('touchend', (ev)=>{
  ev.preventDefault();
  handleDpad(null, false);
});

function handleDpad(dir, down){
  pressedKeys.clear();
  if(down && dir){
    const mapDir = {
      'north': 'arrowup', 'south':'arrowdown', 'west':'arrowleft','east':'arrowright',
      'nw':'q','ne':'e','sw':'z','se':'c'
    };
    if(mapDir[dir]) pressedKeys.add(mapDir[dir]);
  }
}

// Disable double tap zoom
let lastTouch = 0;
document.addEventListener('touchend', function (e) {
  const now = Date.now();
  if (now - lastTouch <= 300) {
    e.preventDefault();
  }
  lastTouch = now;
}, { passive: false });

// Fullscreen
const fsBtn = document.getElementById('fullscreenBtn');
fsBtn.addEventListener('click', async ()=>{
  try{
    if(!document.fullscreenElement) await document.documentElement.requestFullscreen();
    else await document.exitFullscreen();
  }catch(err){}
});

// Game loop
function update(){
  if (gameCompleted) return;

  let dx=0, dy=0;
  if(pressedKeys.has('arrowup') || pressedKeys.has('w')) dy -= 1;
  if(pressedKeys.has('arrowdown') || pressedKeys.has('s')) dy += 1;
  if(pressedKeys.has('arrowleft') || pressedKeys.has('a')) dx -= 1;
  if(pressedKeys.has('arrowright') || pressedKeys.has('d')) dx += 1;
  
  if(dx!==0 && dy!==0){
    dx *= Math.SQRT1_2;
    dy *= Math.SQRT1_2;
  }
  
  player.vx = dx * PLAYER_SPEED;
  player.vy = dy * PLAYER_SPEED;
  player.moving = (dx!==0 || dy!==0);

  const nextX = player.x + player.vx;
  const nextY = player.y + player.vy;
  const nextTileX = Math.floor((nextX)/TILE);
  const nextTileY = Math.floor((nextY)/TILE);
  
  if(isPassable(Math.floor((nextX-8)/TILE), Math.floor((player.y-8)/TILE)) &&
     isPassable(Math.floor((nextX+8)/TILE), Math.floor((player.y+8)/TILE))){
    player.x = nextX;
  }
  if(isPassable(Math.floor((player.x-8)/TILE), Math.floor((nextY-8)/TILE)) &&
     isPassable(Math.floor((player.x+8)/TILE), Math.floor((nextY+8)/TILE))){
    player.y = nextY;
  }

  if(player.vx>0) player.dir='right';
  else if(player.vx<0) player.dir='left';
  else if(player.vy>0) player.dir='down';
  else if(player.vy<0) player.dir='up';

  if(player.moving){
    player.animTick++;
    if(player.animTick>6){ player.animTick=0; player.animFrame=(player.animFrame+1)%4; }
  } else {
    player.animTick++;
    if(player.animTick>12){ player.animTick=0; player.animFrame=0; }
  }

  checkNearbyItems();
}

function draw(){
  ctx.clearRect(0,0,gameCanvas.width,gameCanvas.height);

  for(let y=0;y<MAP_H;y++){
    for(let x=0;x<MAP_W;x++){
      drawTile(ctx, x, y, map[y][x]);
    }
  }

  items.forEach(it => {
    const px = it.xTile * TILE + TILE/2;
    const py = it.yTile * TILE + TILE/2;
    
    if(!it.found) {
      ctx.fillStyle = it.color;
      ctx.fillRect(px-6, py-6, 12, 12);
      
      ctx.fillStyle = '#000';
      ctx.font = '10px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(it.symbol, px, py);
    } else {
      ctx.fillStyle = '#ffd86b';
      ctx.fillRect(px-4, py-4, 8, 8);
    }
  });

  drawPlayer(ctx, player.x, player.y);
}

function addInventoryItem(type){
  const inv = document.getElementById('inventory');
  const div = document.createElement('div');
  div.className='item';
  div.textContent = type;
  inv.appendChild(div);

  setTimeout(() => div.style.transform='scale(1.05)',50);
  setTimeout(() => div.style.transform='',380);
  
  showMessage(`¡Encontraste ${type}!`, 'success');
}

function loop(){
  update();
  draw();
  requestAnimationFrame(loop);
}

// ========== INICIALIZACIÓN ==========
startGameTimer();
loop();

// Cargar leaderboard inicial
loadLeaderboard();
