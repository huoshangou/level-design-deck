#!/usr/bin/env python3
"""
render_deck.py — 生成同一 level 8 个 module 的横向翻页汇报 Deck HTML。

使用：
  python3 tools/render_deck.py --level-id <id> [--output <path>]

输出：outputs/level_<id>__deck.html
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

MODULE_ORDER = [
    "level_overview","bubble_diagram","spatial_layout","atmosphere_ref",
    "lighting_req","vfx_req","audio_req","asset_list",
]
MODULE_META = {
    "level_overview": ("关卡概览","Level Overview"),
    "bubble_diagram": ("流程主线","Flow Diagram"),
    "spatial_layout": ("空间布局","Spatial Layout"),
    "atmosphere_ref": ("氛围参考","Atmosphere Reference"),
    "lighting_req":   ("灯光需求","Lighting Requirements"),
    "vfx_req":        ("视觉特效","VFX Requirements"),
    "audio_req":      ("音频需求","Audio Requirements"),
    "asset_list":     ("资产清单","Asset List"),
}

FS_DARK = (
    "precision highp float;"
    "uniform vec2 u_resolution;uniform float u_time;uniform vec2 u_mouse;"
    "vec3 palette(float t,vec3 a,vec3 b,vec3 c,vec3 d){return a+b*cos(6.28318*(c*t+d));}"
    "void main(){"
    "vec2 uv=gl_FragCoord.xy/u_resolution.xy;"
    "vec2 p=uv*2.0-1.0;p.x*=u_resolution.x/u_resolution.y;"
    "vec2 m=u_mouse*2.0-1.0;m.x*=u_resolution.x/u_resolution.y;"
    "float md=length(p-m);"
    "float mr=sin(md*15.0-u_time*4.0)*exp(-md*3.0);p+=mr*0.08;"
    "vec2 p0=p;"
    "for(float i=1.0;i<4.0;i++){p.x+=0.1/i*sin(i*3.0*p.y+u_time*0.4)+0.05;p.y+=0.1/i*cos(i*2.0*p.x+u_time*0.3)-0.05;}"
    "float r=length(p);float ang=atan(p.y,p.x);"
    "vec3 a=vec3(0.12,0.12,0.13);vec3 b=vec3(0.03,0.04,0.05);"
    "vec3 c=vec3(1.0,1.0,1.0);vec3 d=vec3(0.1,0.2,0.4);"
    "vec3 col=palette(r*1.5+p0.x*0.5+u_time*0.1,a,b,c,d);"
    "float disp=sin(r*25.0-u_time*1.5+ang*2.0)*0.5+0.5;"
    "col+=vec3(disp*0.015,disp*0.01,disp*0.02);"
    "float hi=pow(sin(p.x*4.0+p.y*3.0+u_time)*0.5+0.5,8.0);"
    "col+=hi*0.08;"
    "col=mix(vec3(0.05,0.05,0.06),col,0.85);"
    "gl_FragColor=vec4(col,1.0);}"
)

FS_LIGHT = (
    "precision highp float;"
    "uniform vec2 u_resolution;uniform float u_time;uniform vec2 u_mouse;"
    "float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}"
    "float noise(vec2 p){"
    "vec2 i=floor(p),f=fract(p);"
    "float a=hash(i),b=hash(i+vec2(1,0)),c=hash(i+vec2(0,1)),d=hash(i+vec2(1,1));"
    "vec2 u=f*f*(3.0-2.0*f);"
    "return mix(a,b,u.x)+(c-a)*u.y*(1.0-u.x)+(d-b)*u.x*u.y;}"
    "float fbm(vec2 p){"
    "float v=0.0,a=0.5;mat2 m=mat2(0.80,0.60,-0.60,0.80);"
    "for(int i=0;i<5;i++){v+=a*noise(p);p=m*p*2.02;a*=0.5;}"
    "return v;}"
    "void main(){"
    "vec2 uv=gl_FragCoord.xy/u_resolution.xy;"
    "vec2 p=uv;p.x*=u_resolution.x/u_resolution.y;"
    "vec2 m=u_mouse;m.x*=u_resolution.x/u_resolution.y;"
    "vec2 md=p-m;float dl=length(md);"
    "p+=normalize(md+vec2(0.0001))*exp(-dl*5.0)*0.03;"
    "vec2 q=vec2(fbm(p*1.8+u_time*0.07),fbm(p*1.8+vec2(5.2,1.3)+u_time*0.06));"
    "vec2 r=vec2(fbm(p*2.0+q*1.3+vec2(1.7,9.2)+u_time*0.05),fbm(p*2.0+q*1.3+vec2(8.3,2.8)+u_time*0.04));"
    "float f=fbm(p*2.2+r*1.5);"
    "vec3 col=mix(vec3(0.86,0.85,0.84),vec3(0.955,0.945,0.925),f);"
    "float ph=r.x*2.2+u_time*0.35;"
    "col+=vec3(0.78,0.62,0.92)*sin(ph)*0.055;"
    "col+=vec3(0.55,0.72,0.95)*sin(ph*0.8+2.0)*0.05;"
    "col+=smoothstep(0.48,0.92,f)*0.06;"
    "gl_FragColor=vec4(col,1.0);}"
)

CSS = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--ink:#1f1a14;--ink-rgb:31,26,20;--paper:#f0e6d2;--paper-rgb:240,230,210;--paper-tint:#e3d7bf;--ink-tint:#2d2620;--mono:"IBM Plex Mono",ui-monospace,monospace;--serif-en:"Playfair Display",Georgia,serif;--serif-zh:"Noto Serif SC",serif;--sans-zh:"Noto Sans SC",sans-serif}
html,body{width:100%;height:100%;overflow:hidden;background:#0d0d0f}
canvas.bg{position:fixed;inset:0;width:100vw;height:100vh;z-index:0;display:block;transition:opacity 1.2s ease}
canvas#bg-light{opacity:0}canvas#bg-dark{opacity:1}
body.light-bg canvas#bg-light{opacity:1}body.light-bg canvas#bg-dark{opacity:0}
#deck{position:fixed;inset:0;display:flex;flex-wrap:nowrap;transition:transform .8s cubic-bezier(.77,0,.175,1);z-index:10;will-change:transform}
.slide{width:100vw;height:100vh;flex:0 0 100vw;position:relative;padding:5vh 5vw 9vh 5vw;display:flex;flex-direction:column;overflow:hidden}
.slide.light{color:var(--ink)}.slide.dark{color:var(--paper)}
.slide::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none}
.slide.light::before{background:rgba(var(--paper-rgb),.80);backdrop-filter:blur(3px)}
.slide.dark::before{background:rgba(var(--ink-rgb),.80);backdrop-filter:blur(3px)}
.slide.hero.light::before{background:rgba(var(--paper-rgb),.18);backdrop-filter:none}
.slide.hero.dark::before{background:rgba(var(--ink-rgb),.14);backdrop-filter:none}
.chrome{display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;opacity:.6;margin-bottom:3vh}
.foot{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;opacity:.5}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.3em;text-transform:uppercase;opacity:.6;margin-bottom:1.5vh}
#nav{position:fixed;left:50%;bottom:2.4vh;transform:translateX(-50%);z-index:30;display:flex;gap:10px;padding:7px 13px;border-radius:999px;background:rgba(0,0,0,.2);backdrop-filter:blur(10px)}
.dot{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.3);cursor:pointer;border:0;padding:0;transition:all .3s ease}
.dot:hover{background:rgba(255,255,255,.5);transform:scale(1.15)}
.dot.active{background:rgba(255,255,255,.92);width:22px;border-radius:999px}
body.light-bg .dot{background:rgba(31,26,20,.25)}body.light-bg .dot.active{background:rgba(31,26,20,.88)}
#hint{position:fixed;bottom:2.5vh;right:3vw;z-index:30;font-family:var(--mono);font-size:10px;letter-spacing:.2em;text-transform:uppercase;opacity:.4;color:#aaa}
@keyframes fadein{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.slide.hero h1{animation:fadein .9s .3s both}.slide.hero p{animation:fadein .9s .55s both}
.slide.hero .kicker{animation:fadein .7s .15s both}
.slide.hero .meta-row,.slide.hero [style*="display:flex"]{animation:fadein .8s .7s both}"""

JS_NAV = """
const deck=document.getElementById('deck'),slides=deck.querySelectorAll('.slide'),nav=document.getElementById('nav');
let idx=0,total=slides.length,lock=false;
deck.style.width=(total*100)+'vw';
slides.forEach((s,i)=>{const b=document.createElement('button');b.className='dot';b.dataset.i=i;b.setAttribute('aria-label','Page '+(i+1));b.onclick=()=>go(i);nav.appendChild(b);});
function go(n){if(lock)return;idx=Math.max(0,Math.min(total-1,n));deck.style.transform=`translateX(${-idx*100}vw)`;nav.querySelectorAll('.dot').forEach((d,i)=>d.classList.toggle('active',i===idx));const el=slides[idx];const th=el.dataset.theme||'dark';document.body.classList.toggle('light-bg',th==='light');lock=true;setTimeout(()=>lock=false,600);}
const ov=document.createElement('div');ov.id='overview';ov.style.cssText='position:fixed;inset:0;z-index:100;background:rgba(31,26,20,.92);backdrop-filter:blur(12px);display:none;overflow-y:auto;padding:4vh 4vw';document.body.appendChild(ov);
let overviewOn=false;
function toggleOverview(){overviewOn=!overviewOn;if(overviewOn){ov.innerHTML='';const grid=document.createElement('div');grid.style.cssText='display:grid;grid-template-columns:repeat(4,1fr);gap:2vh 1.6vw;max-width:90vw;margin:0 auto';slides.forEach((s,i)=>{const card=document.createElement('div');card.style.cssText='cursor:pointer;border-radius:4px;overflow:hidden;border:2px solid '+(i===idx?'rgba(240,230,210,.8)':'rgba(240,230,210,.15)');const wrap=document.createElement('div');wrap.style.cssText='width:100%;aspect-ratio:16/9;overflow:hidden;position:relative;pointer-events:none;background:'+(s.classList.contains('light')?'#f0e6d2':'#1f1a14');const clone=s.cloneNode(true);clone.querySelectorAll('iframe').forEach(f=>{const pl=document.createElement('div');pl.style.cssText='flex:1;background:#f5f0e8;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:10px;color:#888;border-radius:2px;margin:8px 0';pl.textContent=f.src.split('/').pop();f.parentNode.replaceChild(pl,f);});clone.style.cssText='width:100vw;height:100vh;transform:scale('+(1/4.5)+');transform-origin:top left;position:absolute;top:0;left:0;pointer-events:none';wrap.appendChild(clone);const label=document.createElement('div');label.style.cssText='padding:5px 8px;font-family:monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#f0e6d2;opacity:.7';label.textContent=(i+1)+' / '+total;card.appendChild(wrap);card.appendChild(label);card.onclick=()=>{toggleOverview();go(i);};grid.appendChild(card);});ov.appendChild(grid);ov.style.display='block';}else{ov.style.display='none';}}
addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();toggleOverview();return;}if(overviewOn)return;if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown')go(idx+1);if(e.key==='ArrowLeft'||e.key==='PageUp')go(idx-1);if(e.key==='Home')go(0);if(e.key==='End')go(total-1);});
let wheelAcc=0;addEventListener('wheel',e=>{wheelAcc+=e.deltaY+e.deltaX;if(Math.abs(wheelAcc)>50){go(idx+(wheelAcc>0?1:-1));wheelAcc=0;}setTimeout(()=>wheelAcc=0,150);},{passive:true});
addEventListener('click',e=>{if(overviewOn)return;if(e.target.closest('#nav')||e.target.closest('#overview'))return;go(idx+(e.clientX>innerWidth/2?1:-1));});
go(0);"""

JS_GL = """
const VS='attribute vec2 position;void main(){gl_Position=vec4(position,0.0,1.0);}';
const mouse={x:0.5,y:0.5};addEventListener('mousemove',e=>{mouse.x=e.clientX/innerWidth;mouse.y=e.clientY/innerHeight});
function bootGL(id,fs){const c=document.getElementById(id);const gl=c.getContext('webgl',{alpha:false,antialias:true});if(!gl)return()=>false;const mk=(t,s)=>{const sh=gl.createShader(t);gl.shaderSource(sh,s);gl.compileShader(sh);return sh};const p=gl.createProgram();gl.attachShader(p,mk(gl.VERTEX_SHADER,VS));gl.attachShader(p,mk(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);gl.useProgram(p);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const pos=gl.getAttribLocation(p,'position');gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);const lR=gl.getUniformLocation(p,'u_resolution'),lT=gl.getUniformLocation(p,'u_time'),lM=gl.getUniformLocation(p,'u_mouse');const resize=()=>{const d=Math.min(window.devicePixelRatio||1,2);c.width=innerWidth*d;c.height=innerHeight*d;gl.viewport(0,0,c.width,c.height);};addEventListener('resize',resize);resize();return(t)=>{gl.uniform2f(lR,c.width,c.height);gl.uniform1f(lT,t);gl.uniform2f(lM,mouse.x,1-mouse.y);gl.drawArrays(gl.TRIANGLES,0,6);return true;};}
const drawDark=bootGL('bg-dark',FS_DARK),drawLight=bootGL('bg-light',FS_LIGHT),t0=Date.now();
(function loop(){const t=(Date.now()-t0)/1000;drawDark(t);drawLight(t);requestAnimationFrame(loop);})();"""


def load_level_meta(level_id):
    spec_path = BASE / "specs" / f"level_overview_{level_id}.spec.json"
    title, intent, level_type = level_id, "", ""
    if spec_path.exists():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            ctx = spec.get("context", {})
            intent = ctx.get("intent", "") or ""
            level_type = ctx.get("level_type", "") or ""
            title = spec.get("title", level_id) or level_id
        except Exception:
            pass
    return title, intent, level_type


def find_modules(level_id):
    outputs = BASE / "outputs"
    return [(k, outputs / f"{k}_{level_id}.html")
            for k in MODULE_ORDER if (outputs / f"{k}_{level_id}.html").exists()]


def render_deck(level_id):
    title, intent, _ = load_level_meta(level_id)
    modules = find_modules(level_id)
    skipped = [k for k in MODULE_ORDER if k not in {m[0] for m in modules}]
    if skipped:
        print(f"[info] skipped (no HTML): {', '.join(skipped)}", file=sys.stderr)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    year = now.year
    mc = len(modules)
    total = 1 + mc + 1

    names_line = " &middot; ".join(f'<span>{MODULE_META[k][0]}</span>' for k, _ in modules)
    cover = f"""<section class="slide hero dark" data-theme="dark">
  <div class="chrome"><div>Level Design Deck &middot; {level_id}</div><div>{date_str} &middot; {mc} Modules</div></div>
  <div style="flex:1;display:grid;gap:3vh;align-content:center">
    <div class="kicker">关卡设计文档 &middot; Level Design Document</div>
    <h1 style="font-family:var(--serif-zh);font-weight:900;font-size:8vw;line-height:.96;letter-spacing:-.02em;">{title}</h1>
    <p style="font-family:var(--serif-zh);font-weight:400;font-size:1.6vw;line-height:1.5;opacity:.82;max-width:60vw;">{intent}</p>
    <div style="display:flex;gap:1.6em;flex-wrap:wrap;font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;opacity:.55;margin-top:1vh">{names_line}</div>
  </div>
  <div class="foot"><div>{level_id} &middot; spec 真源工作台</div><div>github.com/huoshangou/level-design-deck</div></div>
</section>"""

    mod_slides = []
    for i, (key, html_path) in enumerate(modules):
        zh, en = MODULE_META.get(key, (key, key))
        page = i + 2
        fname = html_path.name
        mod_slides.append(f"""<section class="slide light" data-theme="light">
  <div class="chrome"><div>{key} &middot; {zh}</div><div>{page} / {total}</div></div>
  <div style="padding:0 0 2vh;display:flex;flex-direction:column;flex:1;min-height:0;">
    <div class="kicker">Module &middot; {en}</div>
    <iframe src="../outputs/{fname}" loading="lazy" style="flex:1;width:100%;border:1px solid rgba(31,26,20,.15);background:#fff;border-radius:2px;"></iframe>
  </div>
  <div class="foot"><div>来源 &middot; {fname}</div><div>Page {page} &middot; {key}</div></div>
</section>""")

    coda = f"""<section class="slide hero light" data-theme="light">
  <div class="chrome"><div>Coda &middot; 收束</div><div>{total} / {total}</div></div>
  <div style="flex:1;display:grid;gap:4vh;align-content:center">
    <div class="kicker">End of Deck</div>
    <h1 style="font-family:var(--serif-zh);font-weight:900;font-size:6.5vw;line-height:1.1">{mc} 个模块<br>一份关卡设计文档</h1>
    <div style="font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;opacity:.55">{mc} modules &middot; {total} slides &middot; level-design-deck v0.1.0</div>
  </div>
  <div class="foot"><div>End of Deck &middot; {level_id}</div><div>&mdash; {year} &mdash;</div></div>
</section>"""

    slides_html = "\n".join([cover] + mod_slides + [coda])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Deck &middot; {title} &middot; {level_id}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,400&family=IBM+Plex+Mono:wght@300;400;500&family=Noto+Serif+SC:wght@300;400;700;900&family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<canvas id="bg-dark" class="bg"></canvas>
<canvas id="bg-light" class="bg"></canvas>
<div id="deck">
{slides_html}
</div>
<nav id="nav"></nav>
<div id="hint">ESC overview &middot; &larr; &rarr; navigate</div>
<script>
const FS_DARK="{FS_DARK}";
const FS_LIGHT="{FS_LIGHT}";
{JS_GL}
{JS_NAV}
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level-id", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    level_id = args.level_id
    out = Path(args.output) if args.output else BASE / "outputs" / f"level_{level_id}__deck.html"
    html = render_deck(level_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[ok] {out.relative_to(BASE)}  ({len(html.splitlines())} lines)")


if __name__ == "__main__":
    main()
