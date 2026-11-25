// Grava a demonstração: abre o quadro de exemplo num Chrome sem janela, usa mouse e teclado de verdade (CDP),
// confere cada ação e monta MP4 e GIF com ffmpeg. Falha se uma interação não funcionar: o vídeo não mostra o que não roda.
//   node scripts/record.mjs docs/demo.html docs
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [pagina = "docs/demo.html", saida = "docs"] = process.argv.slice(2);
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const W = 1280, H = 800, PORTA = 9347;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "gravar-"));
const dorme = ms => new Promise(ok => setTimeout(ok, ms));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORTA}`, `--user-data-dir=${tmp}/perfil`, `--window-size=${W},${H}`, "--hide-scrollbars", "--force-dark-mode", "about:blank"], { stdio: "ignore" });

let alvo;
for (let i = 0; i < 80 && !alvo; i++) { await dorme(250); try { alvo = (await (await fetch(`http://127.0.0.1:${PORTA}/json`)).json()).find(a => a.type === "page"); } catch {} }
if (!alvo) throw new Error("o Chrome não abriu");
const ws = new WebSocket(alvo.webSocketDebuggerUrl);
await new Promise(ok => (ws.onopen = ok));
let id = 0; const esperas = new Map(), quadros = [], erros = [];
ws.onmessage = m => {
  const d = JSON.parse(m.data);
  if (d.method === "Page.screencastFrame") { const f = `${tmp}/f${String(quadros.length).padStart(5, "0")}.jpg`; fs.writeFileSync(f, Buffer.from(d.params.data, "base64")); quadros.push([f, d.params.metadata.timestamp]); cdp("Page.screencastFrameAck", { sessionId: d.params.sessionId }); return; }
  if (d.method === "Runtime.exceptionThrown") erros.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  esperas.get(d.id)?.(d);
};
const cdp = (method, params = {}) => new Promise(ok => { esperas.set(++id, ok); ws.send(JSON.stringify({ id, method, params })); });
const js = async expression => { const r = await cdp("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description); return r.result?.result?.value; };

await cdp("Page.enable"); await cdp("Runtime.enable");
await cdp("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await cdp("Browser.grantPermissions", { permissions: ["clipboardReadWrite", "clipboardSanitizedWrite"] });
await cdp("Page.navigate", { url: "file://" + path.resolve(pagina) });
await dorme(2500);

// cursor e legenda desenhados na própria página, só para o vídeo
await js(`(() => { const c = document.createElement("div"); c.id = "v-cursor"; c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M5 3l14 8-6 1.6L9.6 19z" fill="#fff" stroke="#111" stroke-width="1.4"/></svg>';
 c.style.cssText = "position:fixed;left:0;top:0;z-index:99;pointer-events:none;transform:translate(640px,420px)"; document.body.append(c);
 const l = document.createElement("div"); l.id = "v-legenda"; l.style.cssText = "position:fixed;left:50%;top:76px;transform:translateX(-50%);z-index:98;pointer-events:none;background:#fff;color:#111;font:600 19px Geist,system-ui,sans-serif;padding:11px 20px;border-radius:999px;box-shadow:0 10px 34px rgba(0,0,0,.45);white-space:nowrap;transition:opacity .3s;opacity:0"; document.body.append(l);
 addEventListener("pointermove", e => { c.style.transform = "translate(" + (e.clientX - 4) + "px," + (e.clientY - 2) + "px)"; }, true); })()`);
const legenda = t => js(`(() => { const l = document.getElementById("v-legenda"); l.textContent = ${JSON.stringify(t)}; l.style.opacity = ${t ? 1 : 0}; l.style.left = document.querySelector(".panel:not([hidden])") ? "calc(50% - 230px)" : "50%"; })()`);

let mx = 640, my = 420;
const mouse = (type, x, y, extra = {}) => cdp("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons: type === "mouseReleased" ? 0 : extra.segurando || type === "mousePressed" ? 1 : 0, clickCount: extra.cliques || 1 });
async function mover(x, y, ms = 550, segurando = false) { const x0 = mx, y0 = my, n = Math.max(2, Math.round(ms / 28)); for (let i = 1; i <= n; i++) { const p = i / n, e = p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; mx = x0 + (x - x0) * e; my = y0 + (y - y0) * e; await mouse("mouseMoved", mx, my, { segurando }); await dorme(24); } }
const centro = async (sel, dx = .5, dy = .5) => { const r = await js(`(() => { const e = ${sel}; if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width * ${dx}, r.top + r.height * ${dy}]; })()`); if (!r) throw new Error("não achei: " + sel); return r; };
async function clicar(sel, dx, dy) { const [x, y] = await centro(sel, dx, dy); await mover(x, y); await mouse("mousePressed", x, y); await dorme(70); await mouse("mouseReleased", x, y); await dorme(250); }
async function arrastar(sel, ax, ay, dx, dy) { const [x, y] = await centro(sel, ax, ay); await mover(x, y); await mouse("mousePressed", x, y); await dorme(150); await mover(x + dx, y + dy, 900, true); await mouse("mouseReleased", x + dx, y + dy); await dorme(350); }
const digitar = async t => { for (const ch of t) { await cdp("Input.insertText", { text: ch }); await dorme(75); } };
const botao = texto => `[...document.querySelectorAll("button")].find(b => b.offsetParent && b.textContent.startsWith(${JSON.stringify(texto)}))`;
const conferidas = [];
const confere = async (nome, expr) => { if (!(await js(expr))) throw new Error("a interação não funcionou: " + nome); conferidas.push(nome); };

await cdp("Page.startScreencast", { format: "jpeg", quality: 90, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
await legenda("Seu pipeline, num quadro que dá para entender"); await dorme(2600);

await legenda("Montado das execuções reais. Arraste os cartões"); const x0 = await js(`window.pipelineBoard.cards.ingest.x`);
await arrastar(`document.querySelector('.card[data-id="ingest"] header h4')`, .5, .5, -30, -70);
await confere("arrastar cartão com o mouse", `window.pipelineBoard.cards.ingest.x !== ${x0}`); await dorme(500);
const w0 = await js(`window.pipelineBoard.cards.ingest.w`);
await legenda("Puxe o canto: as etapas se reorganizam"); await arrastar(`document.querySelector('.card[data-id="ingest"] .grip')`, .5, .5, 190, 0);
await confere("mudar a largura com o mouse", `window.pipelineBoard.cards.ingest.w > ${w0}`); await dorme(900);
await legenda("Um clique volta ao auto layout"); await clicar(botao("Arrumar")); await confere("arrumar", `window.pipelineBoard.cards.ingest.w === ${w0}`); await dorme(1100);

await legenda("Clique numa etapa: o que ela faz por dentro"); await clicar(`window.pipelineBoard.tiles.orders`);
await confere("abrir etapa com clique", `!document.querySelector(".panel").hidden`); await legenda("Clique numa etapa: o que ela faz por dentro"); await dorme(1900);
await legenda("Métricas, registros e o fluxo lido do código");
for (let i = 0; i < 26; i++) { await js(`document.querySelector(".panel").scrollTop += 18`); await dorme(60); }
await dorme(1100); await js(`document.querySelector(".panel").scrollTo({ top: 0, behavior: "smooth" })`); await dorme(700);
await legenda("Copie o contexto e cole no Claude"); await clicar(botao("Copiar contexto")); await dorme(1500);
await clicar(botao("Fechar")); await confere("fechar o painel", `document.querySelector(".panel").hidden`);

await legenda("Busque em etapas, arquivos e fluxos"); await clicar(`document.querySelector(".f-bar .find")`); await digitar("falha");
await confere("busca destaca etapas", `document.querySelectorAll(".step.hit").length > 0`); await dorme(1700);
await js(`(() => { const f = document.querySelector(".f-bar .find"); f.value = ""; f.dispatchEvent(new Event("input")); f.blur(); })()`); await dorme(300);

await legenda("Repita uma execução real e veja onde quebrou"); await clicar(botao("▶ "));
for (let i = 0; i < 120 && !(await js(`!!document.querySelector(".step.broke")`)); i++) await dorme(500);
await confere("o replay termina na falha", `!!document.querySelector(".step.broke")`); await dorme(500); await legenda("Quebrou na publicação"); await dorme(2200);
await legenda("Casos reais explicam o erro"); await clicar(`window.pipelineBoard.tiles.publish`); await legenda("Casos reais explicam o erro"); await dorme(2600);
await clicar(botao("Fechar")); await clicar(botao("Sair")); await dorme(700);

await legenda("Quanto falta para estourar cada limite"); await clicar(botao("Limites")); await legenda("Quanto falta para estourar cada limite"); await confere("painel de limites", `document.querySelectorAll(".limit").length === 3`); await dorme(2800);
await clicar(botao("Fechar"));
await legenda("Relatório: onde o tempo vai"); await clicar(botao("Relatório")); await legenda("Relatório: onde o tempo vai"); await confere("relatório", `document.querySelectorAll(".bars button").length > 5`); await dorme(2600);
await clicar(botao("Fechar"));
await mover(W / 2, H - 150, 500);
await legenda("pipeline-board · um plugin do Claude Code"); await dorme(2800);
await cdp("Page.stopScreencast");

// quadro de capa e capturas para o README
const foto = async nome => fs.writeFileSync(path.join(saida, nome), Buffer.from((await cdp("Page.captureScreenshot", { format: "png" })).result.data, "base64"));
await js(`document.getElementById("v-cursor").remove(); document.getElementById("v-legenda").remove(); window.pipelineBoard.fitAll(true)`); await dorme(700); await foto("quadro.png");
await js(`window.pipelineBoard.openStep("publish")`); await dorme(500); await foto("etapa.png");
await js(`window.pipelineBoard.openLimits()`); await dorme(500); await foto("limites.png");
chrome.kill();
if (erros.length) throw new Error("erros de script na página: " + erros.slice(0, 3).join(" | "));

// cada quadro dura até o seguinte, pelos horários que o Chrome informou
const lista = quadros.map(([f, t], i) => `file '${f}'\nduration ${Math.min(Math.max((quadros[i + 1]?.[1] ?? t + 1.2) - t, 0.01), 4).toFixed(3)}`).join("\n") + `\nfile '${quadros.at(-1)[0]}'\n`;
fs.writeFileSync(`${tmp}/lista.txt`, lista);
const ff = args => execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...args]);
ff(["-f", "concat", "-safe", "0", "-i", `${tmp}/lista.txt`, "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "23", "-preset", "slow", "-movflags", "+faststart", path.join(saida, "demo.mp4")]);
ff(["-i", path.join(saida, "demo.mp4"), "-vf", "fps=10,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", path.join(saida, "demo.gif")]);
console.log(`conferidas com mouse e teclado: ${conferidas.length}\n- ${conferidas.join("\n- ")}\nquadros capturados: ${quadros.length}`);
process.exit(0);
