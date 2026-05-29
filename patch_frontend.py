#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_frontend.py — превращает твой НОВЫЙ стиль index.html в финальную версию:
  • 23 GPU (без RTX 2000 Ada / A4000 / A4500), цены ×4 от RunPod Secure
  • цены и курс приходят с бэкенда (loadPricing), фронтовые — лишь запасной дефолт
  • авто-доступность GPU (индикатор на карточках, обновление раз в минуту)
  • безопасность: убран хардкод admin-email, убран показ SSH-пароля, добавлен esc() (XSS)

ИСПОЛЬЗОВАНИЕ:
  1. Положи этот файл рядом со своим новым index.html
  2. python3 patch_frontend.py
  3. Получишь index_final.html — проверь в браузере и замени им index.html

Скрипт трогает только нужные участки. Если что-то не найдено — честно сообщит
и не тронет файл наугад.

‼ На бэкенде должны существовать (мы их делали в BACKEND_FIXES / INTEGRATION):
   GET /api/gpu/pricing  и  GET /api/gpu/availability
   Без них фронт用 запасной дефолт (сайт не сломается, но цены/доступность статичны).
"""
import sys, os, re

SRC = "index.html"
DST = "index_final.html"
if not os.path.exists(SRC):
    print(f"❌ Положи свой новый {SRC} рядом со скриптом."); sys.exit(1)

html = open(SRC, encoding="utf-8").read()
applied, skipped = [], []

def rep(old, new, label, count=1):
    global html
    if old in html:
        html = html.replace(old, new, count); applied.append(label); return True
    skipped.append(label); return False

# ── НОВЫЕ ДАННЫЕ (сгенерированы из скринов RunPod, ×4) ──
NEW_HOURLY = ("{l4:1.56,a40:1.76,rtx_3090:1.84,rtx_a6000:1.96,rtx_4090:2.76,rtx_6000_ada:3.08,l40:3.28,l40s:3.44,rtx_5090:3.96,a100_pcie:5.56,a100_sxm:5.96,rtx_pro_6000_wk:7.56,rtx_pro_6000:8.36,mi300x:7.96,h100_pcie:11.56,h100_nvl:12.76,h100_sxm:13.16,h200_nvl:15.16,h200_sxm:17.56,b200:23.56,b300:29.56}")

GPUS_RU = open("_ru.txt", encoding="utf-8").read().strip()
GPUS_EN = open("_en.txt", encoding="utf-8").read().strip()
TIERS_NEW = open("_tiers.txt", encoding="utf-8").read().strip()

# ═══════════════════════════════════════════════════════════════
# FIX 1 — rubRate + hourlyUSD + добавить esc(), gpuAvail
# ═══════════════════════════════════════════════════════════════
old1 = ("let lang='RU',selectedGpu=null,cardPeriods={};\n"
"const rubRate=92;\n"
"const hourlyUSD={l4:1.56,rtx_a5000:1.08,rtx_3090:1.84,rtx_4090:2.76,rtx_5090:3.96,rtx_6000_ada:3.08,a40:1.76,l40:3.96,l40s:3.44,rtx_a6000:1.96,a100_pcie:5.56,a100_sxm:5.96,h100_nvl:12.28,h100_pcie:9.56,h100_sxm:11.96,h200:15.96,b200:21.96,rtx_pro_6000:7.56};")
new1 = ("let lang='RU',selectedGpu=null,cardPeriods={};\n"
"/* FIX: курс с бэкенда (loadPricing); 100 — запасной дефолт */\n"
"let rubRate=100;\n"
"let hourlyUSD=" + NEW_HOURLY + ";\n"
"let gpuAvail={}; /* доступность GPU с бэкенда */\n"
"/* FIX: экранирование против XSS */\n"
"function esc(s){return String(s==null?'':s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('\"','&quot;').replaceAll(\"'\",'&#39;');}")
rep(old1, new1, "1: новый hourlyUSD(23) + rubRate=100 + esc() + gpuAvail")

# ═══════════════════════════════════════════════════════════════
# FIX 2 — GPUS RU/EN: заменить целиком объект GPUS={...}
# Берём от "const GPUS={" до "\n};\n\nconst TIERS"
# ═══════════════════════════════════════════════════════════════
m = re.search(r"const GPUS=\{.*?\n\};\n", html, re.DOTALL)
if m:
    new_gpus = "const GPUS={\n  RU:" + GPUS_RU + ",\n  EN:" + GPUS_EN + "\n};\n"
    html = html[:m.start()] + new_gpus + html[m.end():]
    applied.append("2: GPUS RU/EN заменены (23 карты)")
else:
    skipped.append("2: блок const GPUS={...} не найден")

# ═══════════════════════════════════════════════════════════════
# FIX 3 — TIERS заменить
# ═══════════════════════════════════════════════════════════════
m2 = re.search(r"const TIERS=\[.*?\];", html, re.DOTALL)
if m2:
    html = html[:m2.start()] + TIERS_NEW + html[m2.end():]
    applied.append("3: TIERS заменены (entry/mid/pro/elite)")
else:
    skipped.append("3: блок const TIERS=[...] не найден")

# ═══════════════════════════════════════════════════════════════
# FIX 4 — admin: убрать хардкод email/id
# ═══════════════════════════════════════════════════════════════
old4 = "function checkAdminAccess(user){if(!user)return false;const ADMIN_IDS=[1,2];const ADMIN_EMAILS=['mirlan.begaliev@mail.ru'];return ADMIN_IDS.includes(user.id)||ADMIN_EMAILS.includes(user.email);}"
new4 = "function checkAdminAccess(user){return !!(user&&user.is_admin===true);} /* FIX: роль определяет сервер (user.is_admin), без хардкода */"
rep(old4, new4, "4: checkAdminAccess через user.is_admin (убран хардкод)")

# ═══════════════════════════════════════════════════════════════
# FIX 5 — убрать показ SSH-пароля в карточке инстанса
# ═══════════════════════════════════════════════════════════════
ssh_pat = re.compile(r"\$\{inst\.ssh_password\?`<div class=\"access-row\"><span class=\"access-key\">Пароль</span>.*?</div>`:''\}", re.DOTALL)
if ssh_pat.search(html):
    html = ssh_pat.sub("", html, count=1)
    applied.append("5: показ SSH-пароля убран из карточки инстанса")
else:
    skipped.append("5: блок ssh_password в карточке не найден")

# ═══════════════════════════════════════════════════════════════
# FIX 6 — esc() в рендере инстансов и уведомлений (XSS)
# ═══════════════════════════════════════════════════════════════
rep("${inst.gpu_name||inst.gpu_key||'GPU'} · ${inst.instance_name||'instance-'+inst.id}",
    "${esc(inst.gpu_name||inst.gpu_key||'GPU')} · ${esc(inst.instance_name||('instance-'+inst.id))}",
    "6a: esc() имя инстанса")
rep("<div class=\"inst-spec\">${inst.gpu_spec||inst.image_name||'Ubuntu 22.04'}</div>",
    "<div class=\"inst-spec\">${esc(inst.gpu_spec||inst.image_name||'Ubuntu 22.04')}</div>",
    "6b: esc() спека инстанса")
rep("<div class=\"notif-title\">${n.title||''}</div>",
    "<div class=\"notif-title\">${esc(n.title)}</div>", "6c: esc() notif title", count=2)
rep("<div class=\"notif-sub\">${n.body||''}</div>",
    "<div class=\"notif-sub\">${esc(n.body)}</div>", "6d: esc() notif body", count=2)

# ═══════════════════════════════════════════════════════════════
# FIX 7 — loadPricing + loadAvailability + покраска статуса
# Вставляем перед "tryAutoLogin();"
# ═══════════════════════════════════════════════════════════════
anchor7 = "tryAutoLogin();"
inject7 = """/* FIX: тянем цены и курс с бэкенда */
async function loadPricing(){
  try{
    const p=await apiFetch('/api/gpu/pricing');
    if(p&&p.rubRate)rubRate=p.rubRate;
    if(p&&p.hourly)Object.assign(hourlyUSD,p.hourly);
    render();
  }catch(e){console.warn('pricing fallback',e.message);}
}
/* FIX: доступность GPU — красим точку-статус на карточках */
async function loadAvailability(){
  try{
    gpuAvail=await apiFetch('/api/gpu/availability');
    document.querySelectorAll('.gpu-card').forEach(card=>{
      const key=card.id.replace('card-','');
      const st=gpuAvail[key]||'unknown';
      const dot=card.querySelector('.gpu-status');
      if(!dot||card.classList.contains('selected'))return;
      if(st==='high'){dot.style.background='var(--green)';dot.title='В наличии';}
      else if(st==='low'){dot.style.background='var(--orange)';dot.title='Мало';}
      else if(st==='none'){dot.style.background='var(--red)';dot.title='Нет в наличии';}
      else{dot.style.background='rgba(255,255,255,.14)';dot.title='';}
    });
  }catch(e){/* тихо: статус останется нейтральным */}
}
loadPricing();
loadAvailability();
setInterval(loadAvailability,60000);
tryAutoLogin();"""
rep(anchor7, inject7, "7: loadPricing + loadAvailability + автообновление 60с")

# ── запись ──
open(DST, "w", encoding="utf-8").write(html)

print("="*60)
print(f"✅ Готово: {DST}")
print("="*60)
print(f"\nПрименено: {len(applied)}")
for a in applied: print("  ✔", a)
if skipped:
    print(f"\n⚠ Пропущено (участок не найден): {len(skipped)}")
    for s in skipped: print("  •", s)
print("""
Дальше:
  1. Открой index_final.html в браузере, проверь карточки/цены/вход.
  2. Заменишь им свой index.html, закоммить.
‼ Нужны бэкенд-роуты /api/gpu/pricing и /api/gpu/availability (см. INTEGRATION.md).
  Без них сайт работает на запасных ценах (×4) и без живой доступности.
""")
